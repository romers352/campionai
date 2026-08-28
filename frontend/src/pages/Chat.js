import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api, streamChat, ttsAudio, API } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";
import MemoryDrawer from "@/components/MemoryDrawer";
import SettingsDialog from "@/components/SettingsDialog";
import EscalationCard from "@/components/EscalationCard";
import CheckinBanner from "@/components/CheckinBanner";
import { useVisibilityRefetch } from "@/hooks/use-visibility-refetch";
import {
  Plus, ArrowUp, Brain, Settings, LifeBuoy, Menu, Lock,
  MessageSquare, Trash2, Shield, Mic, Volume2, VolumeX, Sparkles, Paperclip, X, Loader2,
} from "lucide-react";

export default function Chat() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [memOpen, setMemOpen] = useState(false);
  const [setOpen, setSetOpen] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [checkin, setCheckin] = useState(null);
  const [handoff, setHandoff] = useState(null);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [speakOn, setSpeakOn] = useState(false);
  const [listening, setListening] = useState(false);
  const [attachment, setAttachment] = useState(null);
  const [uploading, setUploading] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const recognitionRef = useRef(null);
  const audioRef = useRef(null);
  const fileRef = useRef(null);

  const fileUrl = (path) => `${API}/files/${path}?auth=${localStorage.getItem("campion_token")}`;

  const name = user?.profile?.preferred_name || "friend";

  const loadSessions = useCallback(async () => {
    const { data } = await api.get("/sessions");
    setSessions(data);
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => {
    api.get("/checkin").then(({ data }) => { if (data.due) setCheckin(data.message); }).catch(() => {});
    api.get("/voice/status").then(({ data }) => setVoiceEnabled(!!data.enabled)).catch(() => {});
  }, []);
  // Refresh sessions + check-in when returning to the tab.
  useVisibilityRefetch(() => {
    loadSessions();
    api.get("/checkin").then(({ data }) => { if (data.due) setCheckin(data.message); }).catch(() => {});
  });
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, thinking]);

  const speak = async (text) => {
    if (!text) return;
    try {
      if (audioRef.current) { audioRef.current.pause(); }
      const url = await ttsAudio(text);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.play();
    } catch (e) {
      toast.error(e.message || "Voice unavailable");
      setSpeakOn(false);
    }
  };

  const toggleListen = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast.error("Voice input isn't supported in this browser"); return; }
    if (listening) { recognitionRef.current?.stop(); return; }
    const rec = new SR();
    rec.lang = "en-US";
    rec.interimResults = true;
    rec.continuous = false;
    let finalText = "";
    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalText += t; else interim += t;
      }
      setInput((finalText + interim).trim());
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recognitionRef.current = rec;
    setListening(true);
    rec.start();
  };

  const openSession = async (id) => {
    setActiveId(id);
    setMobileNav(false);
    const { data } = await api.get(`/sessions/${id}/messages`);
    setMessages(data.messages.map((m) => ({ id: m.id, role: m.role, content: m.content, image_path: m.image_path })));
  };

  const pickFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.type.startsWith("image/")) { toast.error("Please choose an image"); e.target.value = ""; return; }
    if (f.size > 10 * 1024 * 1024) { toast.error("Image is too large (max 10MB)"); e.target.value = ""; return; }
    setUploading(true);
    const preview = URL.createObjectURL(f);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const { data } = await api.post("/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setAttachment({ path: data.path, preview, name: f.name });
    } catch {
      toast.error("Upload failed");
      URL.revokeObjectURL(preview);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const clearAttachment = () => {
    if (attachment?.preview) URL.revokeObjectURL(attachment.preview);
    setAttachment(null);
  };

  const newChat = () => { setActiveId(null); setMessages([]); setMobileNav(false); };

  const deleteSession = async (e, id) => {
    e.stopPropagation();
    await api.delete(`/sessions/${id}`);
    setSessions((s) => s.filter((x) => x.id !== id));
    if (id === activeId) newChat();
    toast.success("Conversation deleted");
  };

  const send = async (overrideText) => {
    const text = (overrideText ?? input).trim();
    if ((!text && !attachment) || streaming || uploading) return;
    setInput("");
    setCheckin(null);
    const att = attachment;
    setAttachment(null);
    const userMsg = { id: `u-${Date.now()}`, role: "user", content: text, image_preview: att?.preview, image_path: att?.path };
    const aiId = `a-${Date.now()}`;
    setMessages((m) => [...m, userMsg, { id: aiId, role: "assistant", content: "", escalation: null }]);
    setStreaming(true);
    setThinking(true);
    let sessionId = activeId;
    let fullText = "";
    await streamChat({
      body: { session_id: sessionId, message: text, private: user?.private_mode, image_path: att?.path },
      onMeta: (meta) => { sessionId = meta.session_id; if (!activeId) setActiveId(meta.session_id); },
      onDelta: (chunk) => {
        setThinking(false);
        fullText += chunk;
        setMessages((m) => m.map((msg) => msg.id === aiId ? { ...msg, content: msg.content + chunk } : msg));
      },
      onDone: (done) => {
        if (done.escalation?.triggered) setMessages((m) => m.map((msg) => msg.id === aiId ? { ...msg, escalation: done.escalation } : msg));
        if (done.memories_saved > 0) toast("Something worth remembering was saved");
      },
      onError: () => {
        setThinking(false);
        setMessages((m) => m.map((msg) => msg.id === aiId ? { ...msg, content: "I'm here — I just had trouble responding. Try again?" } : msg));
        toast.error("Connection hiccup");
      },
    });
    setStreaming(false);
    setThinking(false);
    if (speakOn && voiceEnabled && fullText) speak(fullText);
    if (!activeId || !sessions.find((s) => s.id === sessionId)) loadSessions();
  };

  const requestHandoff = async () => {
    try {
      const { data } = await api.post("/safety/handoff");
      setHandoff({ ...data, message: "I've connected you with a verified professional. You can reach out whenever you're ready." });
    } catch { toast.error("Could not connect right now"); }
  };

  const onKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } };

  const NavContent = () => (
    <div className="flex flex-col h-full">
      <div className="px-6 py-6">
        <span className="font-display font-semibold text-2xl tracking-tight">Campion<span className="italic font-light">AI</span></span>
      </div>
      <div className="px-4">
        <Button onClick={newChat} variant="outline" className="w-full rounded-full justify-start gap-2 h-11 border-border bg-transparent hover:bg-accent" data-testid="new-chat-button">
          <Plus className="h-4 w-4" /> New conversation
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto px-3 mt-6 space-y-0.5">
        <p className="px-3 text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-2">Recent</p>
        {sessions.map((s) => (
          <button key={s.id} onClick={() => openSession(s.id)} data-testid={`session-${s.id}`}
            className={`group w-full flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-left transition-colors ${activeId === s.id ? "bg-accent" : "hover:bg-accent/50"}`}>
            <MessageSquare className="h-3.5 w-3.5 text-muted-foreground shrink-0" strokeWidth={1.5} />
            <span className="text-sm truncate flex-1 text-foreground/90">{s.title}</span>
            {s.private && <Lock className="h-3 w-3 text-muted-foreground shrink-0" />}
            <span onClick={(e) => deleteSession(e, s.id)} className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-escalation transition-opacity">
              <Trash2 className="h-3.5 w-3.5" />
            </span>
          </button>
        ))}
      </div>
      <div className="p-3 border-t border-border space-y-0.5">
        <NavBtn icon={Sparkles} label={user?.plus?.active ? "CampionAI Plus" : "Upgrade to Plus"} testid="open-wellness-button" onClick={() => navigate("/wellness")} />
        <NavBtn icon={Brain} label="Memory" testid="open-memory-button" onClick={() => { setMemOpen(true); setMobileNav(false); }} />
        <NavBtn icon={LifeBuoy} label="Talk to a human" testid="open-handoff-button" danger onClick={() => { requestHandoff(); setMobileNav(false); }} />
        <NavBtn icon={Settings} label="Settings" testid="open-settings-button" onClick={() => { setSetOpen(true); setMobileNav(false); }} />
        {user?.is_admin && <NavBtn icon={Shield} label="Admin panel" testid="open-admin-button" onClick={() => navigate("/admin")} />}
      </div>
    </div>
  );

  return (
    <div className="h-screen flex bg-background overflow-hidden">
      <aside className="hidden md:flex w-72 border-r border-border flex-col">
        <NavContent />
      </aside>
      <Sheet open={mobileNav} onOpenChange={setMobileNav}>
        <SheetContent side="left" className="w-72 p-0 bg-background border-border">
          <SheetTitle className="sr-only">Navigation menu</SheetTitle>
          <NavContent />
        </SheetContent>
      </Sheet>

      <main className="flex-1 flex flex-col min-w-0">
        <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-5 md:px-8">
          <div className="flex items-center gap-3">
            <button className="md:hidden" onClick={() => setMobileNav(true)} data-testid="mobile-menu-button">
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex items-center gap-2.5">
              <span className="text-[10px] tracking-[0.2em] uppercase border border-border px-2 py-1 text-foreground/60">CampionAI · AI</span>
              {user?.private_mode && (
                <span className="text-[10px] tracking-[0.2em] uppercase flex items-center gap-1 text-muted-foreground"><Lock className="h-3 w-3" /> Private</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {voiceEnabled && (
              <Button variant="ghost" size="icon" className="rounded-full text-muted-foreground hover:text-foreground" data-testid="voice-toggle-button"
                onClick={() => { const n = !speakOn; setSpeakOn(n); if (!n && audioRef.current) audioRef.current.pause(); toast(n ? "CampionAI will speak replies" : "Voice muted"); }}>
                {speakOn ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
              </Button>
            )}
            <Button variant="outline" size="sm" className="rounded-full gap-1.5 border-escalation/40 text-escalation hover:bg-escalation/10 hover:text-escalation" onClick={requestHandoff} data-testid="header-handoff-button">
              <LifeBuoy className="h-4 w-4" /> <span className="hidden sm:inline">Talk to a human</span>
            </Button>
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-6 md:px-8 py-10">
            {checkin && messages.length === 0 && (
              <CheckinBanner
                message={checkin}
                onUse={() => { setMessages([{ id: `c-${Date.now()}`, role: "assistant", content: checkin, escalation: null }]); setCheckin(null); setTimeout(() => inputRef.current?.focus(), 50); }}
                onDismiss={() => setCheckin(null)}
              />
            )}

            {messages.length === 0 && !checkin && (
              <div className="py-24 md:py-32">
                <p className="text-[10px] tracking-[0.25em] uppercase text-muted-foreground mb-6">Good to see you</p>
                <h2 className="font-display font-light text-4xl md:text-5xl tracking-tight mb-4">Hey {name}.</h2>
                <p className="text-muted-foreground text-lg max-w-md leading-relaxed">
                  What's on your mind today — a win, a worry, or just a random thought? I'm listening.
                </p>
              </div>
            )}

            <div className="space-y-10">
              {messages.map((m) => (
                <div key={m.id}>
                  {m.role === "user" ? (
                    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
                      className="ml-auto max-w-[75%] border-l border-border pl-5 flex flex-col items-end gap-2" data-testid="user-message">
                      {(m.image_preview || m.image_path) && (
                        <img src={m.image_preview || fileUrl(m.image_path)} alt="shared" className="rounded-2xl max-h-64 border border-border object-cover" data-testid="message-image" />
                      )}
                      {m.content && <p className="text-base leading-relaxed whitespace-pre-wrap text-foreground/90 text-right">{m.content}</p>}
                    </motion.div>
                  ) : (
                    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} data-testid="ai-message">
                      <p className="text-[10px] tracking-[0.25em] uppercase text-muted-foreground mb-3">CampionAI</p>
                      {m.content ? (
                        <MessageText text={m.content} />
                      ) : thinking ? (
                        <span className="font-ai text-xl font-light text-muted-foreground soft-pulse">thinking…</span>
                      ) : null}
                      {m.escalation && <EscalationCard escalation={m.escalation} />}
                    </motion.div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="px-6 md:px-8 pb-8 pt-2">
          <div className="max-w-3xl mx-auto">
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={pickFile} data-testid="file-input" />
            <div className="rounded-[1.75rem] border border-border bg-white/[0.03] backdrop-blur-md px-2.5 py-2 focus-within:border-foreground/40 transition-colors">
              {attachment && (
                <div className="flex items-center gap-3 px-2 pt-1.5 pb-2.5" data-testid="attachment-preview">
                  <img src={attachment.preview} alt="" className="h-14 w-14 rounded-xl object-cover border border-border" />
                  <span className="text-sm text-muted-foreground truncate flex-1">{attachment.name}</span>
                  <button onClick={clearAttachment} className="text-muted-foreground hover:text-foreground" data-testid="remove-attachment"><X className="h-4 w-4" /></button>
                </div>
              )}
              <div className="flex items-center gap-1.5">
                <button data-testid="attach-button" onClick={() => fileRef.current?.click()} disabled={uploading}
                  className="shrink-0 h-10 w-10 rounded-full flex items-center justify-center text-foreground/60 hover:bg-accent hover:text-foreground transition-colors disabled:opacity-40" title="Share a photo">
                  {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
                </button>
                <button data-testid="mic-button" onClick={toggleListen} title="Speak"
                  className={`shrink-0 h-10 w-10 rounded-full flex items-center justify-center transition-colors ${listening ? "bg-escalation text-white soft-pulse" : "text-foreground/60 hover:bg-accent hover:text-foreground"}`}>
                  <Mic className="h-4 w-4" />
                </button>
                <Textarea
                  data-testid="chat-input"
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={onKey}
                  placeholder={`${listening ? "Listening…" : attachment ? "Add a note (optional)" : "Message CampionAI"}${user?.private_mode ? " · Private Mode" : ""}`}
                  rows={1}
                  className="flex-1 resize-none border-0 bg-transparent focus-visible:ring-0 shadow-none max-h-40 min-h-[40px] leading-[40px] py-0 text-base placeholder:text-muted-foreground"
                />
                <Button data-testid="chat-send-button" onClick={() => send()} disabled={streaming || uploading || (!input.trim() && !attachment)}
                  size="icon" className="rounded-full h-10 w-10 shrink-0 bg-primary text-primary-foreground hover:bg-zinc-200 disabled:opacity-30">
                  <ArrowUp className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground/70 text-center mt-3">
              CampionAI is an AI companion, not a therapist. In an emergency, call your local emergency number.
            </p>
          </div>
        </div>
      </main>

      <MemoryDrawer open={memOpen} onOpenChange={setMemOpen} />
      <SettingsDialog open={setOpen} onOpenChange={setSetOpen} />

      <Dialog open={!!handoff} onOpenChange={(o) => !o && setHandoff(null)}>
        <DialogContent className="bg-popover border-border" data-testid="handoff-dialog">
          <DialogHeader><DialogTitle className="font-display font-light text-2xl">Connecting you with a human</DialogTitle></DialogHeader>
          <DialogDescription className="sr-only">Verified professional and crisis resources</DialogDescription>
          {handoff && <EscalationCard escalation={handoff} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function NavBtn({ icon: Icon, label, onClick, testid, danger }) {
  return (
    <button onClick={onClick} data-testid={testid}
      className={`w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors text-left hover:bg-accent ${danger ? "text-escalation" : "text-foreground/80"}`}>
      <Icon className="h-4 w-4" strokeWidth={1.5} /> {label}
    </button>
  );
}

function MessageText({ text }) {
  const lines = text.split("\n");
  return (
    <div className="font-ai text-xl md:text-[1.35rem] font-light leading-relaxed text-foreground">
      {lines.map((line, li) => {
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={li} className={li > 0 ? "mt-3" : ""}>
            {parts.map((p, i) =>
              p.startsWith("**") && p.endsWith("**")
                ? <strong key={i} className="font-medium">{p.slice(2, -2)}</strong>
                : <span key={i}>{p}</span>
            )}
          </p>
        );
      })}
    </div>
  );
}
