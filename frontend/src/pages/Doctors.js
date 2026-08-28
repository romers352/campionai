import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { toast } from "@/components/ui/sonner";
import AccountMenu from "@/components/AccountMenu";
import RatingStars from "@/components/RatingStars";
import PayPalConsultPay from "@/components/PayPalConsultPay";
import { ArrowLeft, Loader2, Video, Phone, MessageSquare, Stethoscope, Globe, Heart, Search, X } from "lucide-react";

const LANGUAGES = [
  ["", "Any language"], ["en", "English"], ["hi", "Hindi"], ["ne", "Nepali"],
  ["es", "Spanish"], ["fr", "French"], ["ar", "Arabic"], ["pt", "Portuguese"], ["bn", "Bengali"],
];
const MODES = [
  { id: "video", label: "Video", icon: Video },
  { id: "audio", label: "Audio", icon: Phone },
  { id: "chat", label: "Chat", icon: MessageSquare },
];

const initials = (name = "") =>
  name.replace(/^dr\.?\s*/i, "").split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

function DoctorAvatar({ doc }) {
  const [err, setErr] = useState(false);
  if (doc.photo_path && !err) {
    return <img src={doc.photo_path} alt="" onError={() => setErr(true)}
      className="h-14 w-14 rounded-2xl object-cover border border-border shrink-0" />;
  }
  return (
    <div className="h-14 w-14 rounded-2xl border border-border bg-white/[0.04] flex items-center justify-center shrink-0">
      <span className="font-display text-lg text-foreground/80">{initials(doc.name) || "Dr"}</span>
    </div>
  );
}

function DoctorSkeleton() {
  return (
    <div className="bg-card/60 p-5 flex items-center gap-4 animate-pulse">
      <div className="h-14 w-14 rounded-2xl bg-white/[0.05] shrink-0" />
      <div className="flex-1 space-y-2.5">
        <div className="h-4 w-40 rounded bg-white/[0.06]" />
        <div className="h-3 w-56 rounded bg-white/[0.04]" />
        <div className="h-3 w-32 rounded bg-white/[0.04]" />
      </div>
      <div className="h-9 w-24 rounded-full bg-white/[0.05] shrink-0" />
    </div>
  );
}

export default function Doctors() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [docs, setDocs] = useState(null);
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState("");
  const [volunteerOnly, setVolunteerOnly] = useState(false);
  const [onlineOnly, setOnlineOnly] = useState(false);
  const [booking, setBooking] = useState(null);   // the doctor being booked
  const [mode, setMode] = useState("video");
  const [when, setWhen] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(null);   // {session, order_id} awaiting payment

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/doctors", {
        params: {
          language: language || undefined, volunteer_only: volunteerOnly,
          online_only: onlineOnly, q: query.trim() || undefined,
        },
      });
      setDocs(data);
    } catch {
      toast.error("Couldn't load doctors");
      setDocs([]);
    }
  }, [language, volunteerOnly, onlineOnly, query]);

  // Debounce so typing in search doesn't hammer the API.
  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  const afterCreate = (data, doctorName) => {
    if (data.requires_payment) {
      setPending({ session: data.session, orderId: data.order_id, doctorName });
    } else {
      setBooking(null);
      if (data.session.status === "requested") {
        toast.success("Request sent — hold tight while a doctor picks it up.");
        navigate(`/consult/${data.session.id}`);
      } else {
        toast.success("Booked. You'll get a reminder before it starts.");
        navigate("/consults");
      }
    }
  };

  const talkNow = async (doctor) => {
    setBusy(true);
    try {
      const { data } = await api.post("/consults/request", { doctor_id: doctor.id, mode });
      afterCreate(data, doctor.name);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't start the session");
    } finally { setBusy(false); }
  };

  const book = async () => {
    if (!when) return toast.error("Pick a date and time");
    setBusy(true);
    try {
      const { data } = await api.post("/consults/book", {
        doctor_id: booking.id, scheduled_at: new Date(when).toISOString(), mode, note: note || undefined,
      });
      afterCreate(data, booking.name);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't book that slot");
    } finally { setBusy(false); }
  };

  const onPaid = (session) => {
    setPending(null);
    setBooking(null);
    toast.success("Paid — you're all set.");
    navigate(session.kind === "instant" ? `/consult/${session.id}` : "/consults");
  };

  const onlineCount = Array.isArray(docs) ? docs.filter((d) => d.is_online).length : 0;

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate("/chat")} data-testid="doctors-back-button">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <span className="font-display font-semibold text-xl tracking-tight">Talk to a doctor</span>
        </div>
        <AccountMenu />
      </header>

      <div className="max-w-4xl mx-auto px-6 py-10">
        <p className="text-muted-foreground mb-6 max-w-xl leading-relaxed">
          Real, verified people — not the AI. Volunteers are free; others set their own rate.
          Matched to <span className="text-foreground">{user?.country || "your region"}</span> and your language.
          {Array.isArray(docs) && docs.length > 0 && (
            <span className="text-foreground/70"> · {onlineCount} online now</span>
          )}
        </p>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or specialty…"
            className="rounded-full h-11 pl-11 pr-10"
            data-testid="doctor-search"
          />
          {query && (
            <button onClick={() => setQuery("")} className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground" data-testid="doctor-search-clear">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-end gap-3 mb-8">
          <div className="w-44">
            <Label className="text-xs text-muted-foreground">Language</Label>
            <Select value={language || "any"} onValueChange={(v) => setLanguage(v === "any" ? "" : v)}>
              <SelectTrigger className="mt-1.5 rounded-full h-10" data-testid="filter-language"><SelectValue /></SelectTrigger>
              <SelectContent>
                {LANGUAGES.map(([v, l]) => <SelectItem key={v || "any"} value={v || "any"}>{l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button variant={volunteerOnly ? "default" : "outline"} className="rounded-full h-10 gap-2"
            onClick={() => setVolunteerOnly((v) => !v)} data-testid="filter-volunteer">
            <Heart className="h-3.5 w-3.5" /> Free only
          </Button>
          <Button variant={onlineOnly ? "default" : "outline"} className="rounded-full h-10 gap-2"
            onClick={() => setOnlineOnly((v) => !v)} data-testid="filter-online">
            <span className="h-2 w-2 rounded-full bg-emerald-400" /> Online now
          </Button>
          <div className="ml-auto flex gap-1 rounded-full border border-border p-1">
            {MODES.map((m) => (
              <button key={m.id} onClick={() => setMode(m.id)} data-testid={`mode-${m.id}`}
                className={`rounded-full px-3 py-1.5 text-xs flex items-center gap-1.5 transition-colors ${mode === m.id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                <m.icon className="h-3.5 w-3.5" /> {m.label}
              </button>
            ))}
          </div>
        </div>

        {docs === null ? (
          <div className="space-y-px bg-border border border-border rounded-2xl overflow-hidden" data-testid="doctors-loading">
            {[0, 1, 2, 3].map((i) => <DoctorSkeleton key={i} />)}
          </div>
        ) : docs.length === 0 ? (
          <div className="rounded-2xl border border-border bg-card/30 p-10 text-center" data-testid="doctors-empty">
            <Stethoscope className="h-7 w-7 text-muted-foreground mx-auto mb-4" strokeWidth={1.5} />
            <p className="font-medium mb-1">No doctors match yet</p>
            <p className="text-sm text-muted-foreground mb-5">
              {query ? `Nothing for "${query}". Try a different search or clear the filters.` : "Try clearing the filters, or check back a little later."}
            </p>
            {(query || language || volunteerOnly || onlineOnly) && (
              <Button variant="outline" className="rounded-full" onClick={() => { setQuery(""); setLanguage(""); setVolunteerOnly(false); setOnlineOnly(false); }}>
                Clear all filters
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-px bg-border border border-border rounded-2xl overflow-hidden" data-testid="doctors-list">
            {docs.map((d, idx) => (
              <motion.div key={d.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.04 }}
                className="bg-card/60 hover:bg-card/80 transition-colors p-5 flex flex-col sm:flex-row sm:items-center gap-4" data-testid={`doctor-${d.id}`}>
                <DoctorAvatar doc={d} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <p className="font-medium truncate">{d.name}</p>
                    {d.is_online && <span className="text-[10px] tracking-[0.15em] uppercase text-emerald-400 flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Online</span>}
                    {d.is_volunteer && <span className="text-[10px] tracking-[0.15em] uppercase border border-border px-2 py-0.5 rounded-full text-muted-foreground">Volunteer</span>}
                  </div>
                  <p className="text-sm text-muted-foreground truncate">{d.credentials}</p>
                  {d.specialty && (
                    <span className="inline-block mt-1.5 text-[11px] tracking-[0.06em] text-foreground/70 border border-border rounded-full px-2.5 py-0.5">{d.specialty}</span>
                  )}
                  {d.bio && <p className="text-sm text-muted-foreground/80 mt-2 line-clamp-2 leading-relaxed">{d.bio}</p>}
                  <div className="flex items-center gap-3 mt-2 flex-wrap">
                    <RatingStars value={d.rating_avg} count={d.rating_count} testid={`rating-${d.id}`} />
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Globe className="h-3 w-3" /> {d.country} · {(d.languages || []).join(", ").toUpperCase()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0 self-start sm:self-center">
                  <div className="text-right">
                    <span className="font-display font-light text-2xl block leading-none">
                      {d.session_price > 0 ? `$${d.session_price}` : "Free"}
                    </span>
                    <span className="text-[10px] tracking-[0.15em] uppercase text-muted-foreground">per session</span>
                  </div>
                  <Button variant="outline" className="rounded-full border-border" onClick={() => { setBooking(d); setWhen(""); setNote(""); }}
                    data-testid={`book-${d.id}`}>
                    Book
                  </Button>
                  <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200"
                    disabled={!d.is_online || busy} onClick={() => talkNow(d)} data-testid={`talknow-${d.id}`}>
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Talk now"}
                  </Button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Booking / payment dialog */}
      <Dialog open={!!booking} onOpenChange={(o) => { if (!o) { setBooking(null); setPending(null); } }}>
        <DialogContent className="max-w-md" data-testid="book-dialog">
          <DialogHeader>
            <DialogTitle className="font-display">
              {pending ? "Confirm and pay" : `Book ${booking?.name}`}
            </DialogTitle>
            <DialogDescription>
              {pending
                ? `$${pending.session.price} for a ${pending.session.mode} session with ${pending.doctorName}.`
                : "Pick a time that works. You'll both get a reminder."}
            </DialogDescription>
          </DialogHeader>

          {pending ? (
            <PayPalConsultPay
              sessionId={pending.session.id}
              orderId={pending.orderId}
              onPaid={() => onPaid(pending.session)}
            />
          ) : (
            <div className="space-y-4">
              <div>
                <Label className="text-sm">Date & time</Label>
                <Input type="datetime-local" className="mt-1.5 rounded-full h-10" value={when}
                  onChange={(e) => setWhen(e.target.value)} data-testid="book-datetime" />
              </div>
              <div>
                <Label className="text-sm">Anything they should know? (optional)</Label>
                <Input className="mt-1.5 rounded-full h-10" value={note} placeholder="A sentence is plenty"
                  onChange={(e) => setNote(e.target.value)} data-testid="book-note" />
              </div>
              <div className="flex items-center justify-between pt-2">
                <span className="text-sm text-muted-foreground">
                  {booking?.session_price > 0 ? `$${booking.session_price} · ${mode}` : `Free · ${mode}`}
                </span>
                <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200"
                  onClick={book} disabled={busy} data-testid="book-confirm">
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Confirm booking"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
