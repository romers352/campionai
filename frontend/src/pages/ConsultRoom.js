import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";
import RatingStars from "@/components/RatingStars";
import useWebRTC from "@/hooks/useWebRTC";
import {
  Mic, MicOff, Video, VideoOff, PhoneOff, Send, Loader2, AlertTriangle, MessageSquare,
} from "lucide-react";

export default function ConsultRoom() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [session, setSession] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [showChat, setShowChat] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [rateOpen, setRateOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const chatEnd = useRef(null);

  const isDoctor = user?.role === "doctor";

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, m] = await Promise.all([
          api.get(`/consults/${sessionId}`),
          api.get(`/consults/${sessionId}/messages`),
        ]);
        if (cancelled) return;
        setSession(s.data);
        setMessages(m.data);
      } catch (e) {
        if (!cancelled) setLoadError(e?.response?.data?.detail || "Couldn't open this session");
      }
    })();
    return () => { cancelled = true; };
  }, [sessionId]);

  const onChat = useCallback((msg) => setMessages((prev) => [...prev, msg]), []);
  const onEnded = useCallback(() => {
    // Only the patient rates, and only once the call actually happened.
    if (!isDoctor) setRateOpen(true);
  }, [isDoctor]);

  const rtc = useWebRTC({
    sessionId,
    mode: session?.mode || "video",
    isDoctor,
    onChat,
    onEnded,
  });

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, showChat]);

  const send = () => {
    if (!draft.trim()) return;
    rtc.sendChat(draft);
    setDraft("");
  };

  const submitRating = async () => {
    if (!rating) return toast.error("Pick a star rating");
    setSubmitting(true);
    try {
      await api.post(`/consults/${sessionId}/rate`, { stars: rating, comment: comment || undefined });
      toast.success("Thanks — that helps the next person choose.");
      navigate("/consults");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't save your rating");
    } finally { setSubmitting(false); }
  };

  if (loadError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="max-w-sm text-center" data-testid="consult-error">
          <AlertTriangle className="h-8 w-8 text-muted-foreground mx-auto mb-5" strokeWidth={1.2} />
          <p className="font-display font-light text-2xl mb-3">Can't open this session</p>
          <p className="text-muted-foreground mb-8">{loadError}</p>
          <Button variant="outline" className="rounded-full border-border" onClick={() => navigate("/consults")}>My sessions</Button>
        </div>
      </div>
    );
  }

  if (!session) {
    return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const other = isDoctor ? session.user_name : session.doctor_name;
  const isChatOnly = session.mode === "chat";
  const statusCopy = {
    connecting: "Connecting…",
    waiting: `Waiting for ${other} to join…`,
    live: "Connected",
    ended: "Session ended",
    failed: "Couldn't connect",
  }[rtc.status];

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="consult-room">
      <header className="glass h-16 flex items-center justify-between px-6 shrink-0">
        <div className="min-w-0">
          <p className="font-medium truncate">{other}</p>
          <p className="text-xs text-muted-foreground" data-testid="consult-status">{statusCopy}</p>
        </div>
        <div className="flex items-center gap-2">
          {!isChatOnly && (
            <Button variant="ghost" size="icon" className="rounded-full md:hidden" onClick={() => setShowChat((s) => !s)} data-testid="toggle-chat">
              <MessageSquare className="h-4 w-4" />
            </Button>
          )}
        </div>
      </header>

      {rtc.error && (
        <div className="bg-escalation/10 border-b border-escalation/30 px-6 py-3 flex items-center gap-3" data-testid="consult-banner">
          <AlertTriangle className="h-4 w-4 text-escalation shrink-0" />
          <p className="text-sm text-foreground/85">{rtc.error}</p>
        </div>
      )}

      <div className="flex-1 flex min-h-0">
        {!isChatOnly && (
          <div className="relative flex-1 bg-black/40 min-h-0">
            <video ref={rtc.remoteVideo} autoPlay playsInline
              className="h-full w-full object-cover" data-testid="remote-video" />
            {(!rtc.peerPresent || !rtc.peerMedia.cam) && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center">
                  <div className="h-20 w-20 rounded-full border border-border bg-card/60 flex items-center justify-center mx-auto mb-4">
                    <span className="font-display font-light text-3xl">{(other || "?").charAt(0).toUpperCase()}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {rtc.peerPresent ? `${other}'s camera is off` : statusCopy}
                  </p>
                </div>
              </div>
            )}
            <video ref={rtc.localVideo} autoPlay playsInline muted
              className="absolute bottom-5 right-5 h-32 w-24 sm:h-40 sm:w-28 rounded-xl object-cover border border-border bg-black"
              data-testid="local-video" />
          </div>
        )}

        <aside className={`${isChatOnly ? "flex-1" : "w-full md:w-80 border-l border-border"} ${!isChatOnly && !showChat ? "hidden md:flex" : "flex"} flex-col min-h-0`}>
          <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="consult-messages">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                Messages here stay between you two — the AI never sees them.
              </p>
            )}
            {messages.map((m) => {
              const mine = isDoctor ? m.sender_role === "doctor" : m.sender_role === "user";
              return (
                <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${mine ? "bg-primary text-primary-foreground" : "bg-card border border-border"}`}>
                    {m.text}
                  </div>
                </div>
              );
            })}
            <div ref={chatEnd} />
          </div>
          <div className="border-t border-border p-3 flex gap-2">
            <Textarea rows={1} value={draft} placeholder="Write a message…"
              className="resize-none rounded-2xl min-h-[42px] max-h-32"
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
              disabled={rtc.status === "ended" || rtc.status === "failed"}
              data-testid="consult-chat-input" />
            <Button size="icon" className="rounded-full shrink-0 h-[42px] w-[42px]" onClick={send}
              disabled={!draft.trim() || rtc.status === "ended"} data-testid="consult-chat-send">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </aside>
      </div>

      <div className="glass h-20 flex items-center justify-center gap-3 shrink-0">
        {!isChatOnly && (
          <>
            <Button variant="outline" size="icon"
              className={`rounded-full h-12 w-12 border-border ${!rtc.micOn ? "bg-escalation/15 border-escalation/40" : ""}`}
              onClick={rtc.toggleMic} data-testid="toggle-mic" aria-label={rtc.micOn ? "Mute" : "Unmute"}>
              {rtc.micOn ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5 text-escalation" />}
            </Button>
            {session.mode === "video" && (
              <Button variant="outline" size="icon"
                className={`rounded-full h-12 w-12 border-border ${!rtc.camOn ? "bg-escalation/15 border-escalation/40" : ""}`}
                onClick={rtc.toggleCam} data-testid="toggle-cam" aria-label={rtc.camOn ? "Turn camera off" : "Turn camera on"}>
                {rtc.camOn ? <Video className="h-5 w-5" /> : <VideoOff className="h-5 w-5 text-escalation" />}
              </Button>
            )}
          </>
        )}
        <Button className="rounded-full h-12 px-7 bg-escalation hover:bg-escalation/90 gap-2"
          onClick={() => { rtc.hangup(); }} disabled={rtc.status === "ended"} data-testid="hangup">
          <PhoneOff className="h-5 w-5" /> {isChatOnly ? "End chat" : "Leave"}
        </Button>
      </div>

      <Dialog open={rateOpen} onOpenChange={setRateOpen}>
        <DialogContent className="max-w-sm" data-testid="rate-dialog">
          <DialogHeader>
            <DialogTitle className="font-display">How was it?</DialogTitle>
            <DialogDescription>Your rating helps the next person find the right doctor.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex justify-center py-2">
              <RatingStars value={rating} onChange={setRating} size="h-8 w-8" testid="rate" />
            </div>
            <Input placeholder="Anything you'd add? (optional)" className="rounded-full h-10"
              value={comment} onChange={(e) => setComment(e.target.value)} data-testid="rate-comment" />
            <div className="flex gap-2">
              <Button variant="outline" className="rounded-full flex-1 border-border"
                onClick={() => navigate("/consults")} data-testid="rate-skip">Skip</Button>
              <Button className="rounded-full flex-1 bg-primary text-primary-foreground hover:bg-zinc-200"
                onClick={submitRating} disabled={submitting} data-testid="rate-submit">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
