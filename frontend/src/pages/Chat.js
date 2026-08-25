import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api, streamChat } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";
import MemoryDrawer from "@/components/MemoryDrawer";
import SettingsDialog from "@/components/SettingsDialog";
import EscalationCard from "@/components/EscalationCard";
import CheckinBanner from "@/components/CheckinBanner";
import {
  HeartHandshake, Plus, Send, Brain, Settings, LifeBuoy, Menu, Lock,
  MessageCircle, Trash2, Shield, Loader2,
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
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  const name = user?.profile?.preferred_name || "friend";

  const loadSessions = useCallback(async () => {
    const { data } = await api.get("/sessions");
    setSessions(data);
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  useEffect(() => {
    api.get("/checkin").then(({ data }) => { if (data.due) setCheckin(data.message); }).catch(() => {});
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, thinking]);

  const openSession = async (id) => {
    setActiveId(id);
    setMobileNav(false);
    const { data } = await api.get(`/sessions/${id}/messages`);
    setMessages(data.messages.map((m) => ({ id: m.id, role: m.role, content: m.content })));
  };

  const newChat = () => {
    setActiveId(null);
    setMessages([]);
    setMobileNav(false);
  };

  const deleteSession = async (e, id) => {
    e.stopPropagation();
    await api.delete(`/sessions/${id}`);
    setSessions((s) => s.filter((x) => x.id !== id));
    if (id === activeId) newChat();
    toast.success("Conversation deleted");
  };

  const send = async (overrideText) => {
    const text = (overrideText ?? input).trim();
    if (!text || streaming) return;
    setInput("");
    setCheckin(null);
    const userMsg = { id: `u-${Date.now()}`, role: "user", content: text };
    const aiId = `a-${Date.now()}`;
    setMessages((m) => [...m, userMsg, { id: aiId, role: "assistant", content: "", escalation: null }]);
    setStreaming(true);
    setThinking(true);

    let sessionId = activeId;
    await streamChat({
      body: { session_id: sessionId, message: text, private: user?.private_mode },
      onMeta: (meta) => {
        sessionId = meta.session_id;
        if (!activeId) setActiveId(meta.session_id);
      },
      onDelta: (chunk) => {
        setThinking(false);
        setMessages((m) => m.map((msg) => msg.id === aiId ? { ...msg, content: msg.content + chunk } : msg));
      },
      onDone: (done) => {
        if (done.escalation?.triggered) {
          setMessages((m) => m.map((msg) => msg.id === aiId ? { ...msg, escalation: done.escalation } : msg));
        }
        if (done.memories_saved > 0) toast("Something worth remembering was saved", { icon: "🧠" });
      },
      onError: () => {
        setThinking(false);
        setMessages((m) => m.map((msg) => msg.id === aiId ? { ...msg, content: "I'm here — I just had trouble responding. Try again?" } : msg));
        toast.error("Connection hiccup");
      },
    });
    setStreaming(false);
    setThinking(false);
    if (!activeId || !sessions.find((s) => s.id === sessionId)) loadSessions();
  };

  const requestHandoff = async () => {
    try {
      const { data } = await api.post("/safety/handoff");
      setHandoff({ ...data, message: "I've connected you with a verified professional. You can reach out whenever you're ready." });
    } catch {
      toast.error("Could not connect right now");
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const NavContent = () => (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="h-8 w-8 rounded-xl bg-primary flex items-center justify-center">
          <HeartHandshake className="h-4 w-4 text-primary-foreground" />
        </div>
        <span className="font-display font-extrabold text-lg">CampionAI</span>
      </div>

      <div className="px-4">
        <Button onClick={newChat} className="w-full rounded-full justify-start gap-2 h-11" data-testid="new-chat-button">
          <Plus className="h-4 w-4" /> New conversation
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 mt-4 space-y-1">
        {sessions.map((s) => (
          <button key={s.id} onClick={() => openSession(s.id)} data-testid={`session-${s.id}`}
            className={`group w-full flex items-center gap-2.5 rounded-2xl px-3 py-2.5 text-left transition-colors ${activeId === s.id ? "bg-accent" : "hover:bg-accent/60"}`}>
            <MessageCircle className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="text-sm truncate flex-1">{s.title}</span>
            {s.private && <Lock className="h-3 w-3 text-primary shrink-0" />}
            <span onClick={(e) => deleteSession(e, s.id)} className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-escalation transition-all">
              <Trash2 className="h-3.5 w-3.5" />
            </span>
          </button>
        ))}
      </div>

      <div className="p-3 border-t border-border/60 space-y-1">
        <NavBtn icon={Brain} label="Memory" testid="open-memory-button" onClick={() => { setMemOpen(true); setMobileNav(false); }} />
        <NavBtn icon={LifeBuoy} label="Talk to a human" testid="open-handoff-button" onClick={() => { requestHandoff(); setMobileNav(false); }} />
        <NavBtn icon={Settings} label="Settings" testid="open-settings-button" onClick={() => { setSetOpen(true); setMobileNav(false); }} />
        {user?.is_admin && <NavBtn icon={Shield} label="Admin panel" testid="open-admin-button" onClick={() => navigate("/admin")} />}
      </div>
    </div>
  );

  return (
    <div className="h-screen flex bg-background overflow-hidden">
      <aside className="hidden md:flex w-72 border-r border-border/60 bg-card/40 flex-col">
        <NavContent />
      </aside>

      <Sheet open={mobileNav} onOpenChange={setMobileNav}>
        <SheetContent side="left" className="w-72 p-0">
          <NavContent />
        </SheetContent>
      </Sheet>

      <main className="flex-1 flex flex-col min-w-0">
        <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-3">
            <button className="md:hidden" onClick={() => setMobileNav(true)} data-testid="mobile-menu-button">
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <p className="font-display font-bold leading-tight">CampionAI</p>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {user?.private_mode ? <><Lock className="h-3 w-3" /> Private Mode</> : "Always here for you"}
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" className="rounded-full gap-1.5" onClick={requestHandoff} data-testid="header-handoff-button">
            <LifeBuoy className="h-4 w-4" /> <span className="hidden sm:inline">Talk to a human</span>
          </Button>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-5 md:px-6 py-8">
            {checkin && messages.length === 0 && (
              <CheckinBanner
                message={checkin}
                onUse={() => {
                  setMessages([{ id: `c-${Date.now()}`, role: "assistant", content: checkin, escalation: null }]);
                  setCheckin(null);
                  setTimeout(() => inputRef.current?.focus(), 50);
                }}
                onDismiss={() => setCheckin(null)}
              />
            )}

            {messages.length === 0 && !checkin && (
              <div className="text-center py-20">
                <div className="h-14 w-14 rounded-3xl bg-primary/12 flex items-center justify-center mx-auto mb-6">
                  <HeartHandshake className="h-7 w-7 text-primary" />
                </div>
                <h2 className="text-2xl font-extrabold font-display tracking-tight mb-2">Hey {name} 👋</h2>
                <p className="text-muted-foreground max-w-sm mx-auto">
                  What's on your mind today? A win, a worry, or just a random thought — I'm listening.
                </p>
              </div>
            )}

            <div className="space-y-6">
              {messages.map((m) => (
                <div key={m.id}>
                  {m.role === "user" ? (
                    <div className="flex justify-end">
                      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
                        className="rounded-3xl rounded-br-md bg-secondary text-secondary-foreground px-5 py-3 max-w-[80%] text-[15px] leading-relaxed whitespace-pre-wrap" data-testid="user-message">
                        {m.content}
                      </motion.div>
                    </div>
                  ) : (
                    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
                      className="flex gap-3" data-testid="ai-message">
                      <div className="h-8 w-8 rounded-full bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
                        <HeartHandshake className="h-4 w-4 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        {m.content ? (
                          <MessageText text={m.content} />
                        ) : thinking ? (
                          <span className="shimmer-text text-[15px] font-medium">CampionAI is thinking…</span>
                        ) : null}
                        {m.escalation && <EscalationCard escalation={m.escalation} />}
                      </div>
                    </motion.div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="px-5 md:px-6 pb-6 pt-2">
          <div className="max-w-3xl mx-auto">
            <div className="relative flex items-end gap-2 rounded-[1.75rem] border border-border bg-card p-2 ambient-shadow focus-within:border-primary/50 transition-colors">
              <Textarea
                data-testid="chat-input"
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKey}
                placeholder={`Message CampionAI${user?.private_mode ? " (Private Mode)" : ""}…`}
                rows={1}
                className="flex-1 resize-none border-0 bg-transparent focus-visible:ring-0 shadow-none max-h-40 text-[15px] py-2.5"
              />
              <Button data-testid="chat-send-button" onClick={() => send()} disabled={streaming || !input.trim()}
                size="icon" className="rounded-full h-10 w-10 shrink-0">
                {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-[11px] text-muted-foreground text-center mt-2.5">
              CampionAI is an AI companion, not a therapist. In an emergency, call your local emergency number.
            </p>
          </div>
        </div>
      </main>

      <MemoryDrawer open={memOpen} onOpenChange={setMemOpen} />
      <SettingsDialog open={setOpen} onOpenChange={setSetOpen} />

      <Dialog open={!!handoff} onOpenChange={(o) => !o && setHandoff(null)}>
        <DialogContent data-testid="handoff-dialog">
          <DialogHeader><DialogTitle className="font-display">Connecting you with a human</DialogTitle></DialogHeader>
          {handoff && <EscalationCard escalation={handoff} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function NavBtn({ icon: Icon, label, onClick, testid }) {
  return (
    <button onClick={onClick} data-testid={testid}
      className="w-full flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm hover:bg-accent transition-colors text-left">
      <Icon className="h-4 w-4 text-muted-foreground" /> {label}
    </button>
  );
}

function MessageText({ text }) {
  const lines = text.split("\n");
  return (
    <div className="text-[15px] leading-relaxed">
      {lines.map((line, li) => {
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={li} className={li > 0 ? "mt-2" : ""}>
            {parts.map((p, i) =>
              p.startsWith("**") && p.endsWith("**")
                ? <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong>
                : <span key={i}>{p}</span>
            )}
          </p>
        );
      })}
    </div>
  );
}
