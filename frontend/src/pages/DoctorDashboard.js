import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/sonner";
import AccountMenu from "@/components/AccountMenu";
import RatingStars from "@/components/RatingStars";
import { Loader2, Trash2, Plus, Video, Phone, MessageSquare, Wallet } from "lucide-react";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const MODE_ICON = { video: Video, audio: Phone, chat: MessageSquare };
const MODE_LABEL = { video: "Video call", audio: "Audio call", chat: "Chat" };
const HEARTBEAT_MS = 30000;   // server treats >90s without a ping as offline

const initials = (name = "") =>
  name.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";

const PatientAvatar = ({ name }) => (
  <div className="h-9 w-9 rounded-full border border-border bg-white/[0.04] flex items-center justify-center shrink-0">
    <span className="text-xs font-medium text-foreground/80">{initials(name)}</span>
  </div>
);

const fmt = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return "—"; }
};

export default function DoctorDashboard() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [inbox, setInbox] = useState([]);
  const [slots, setSlots] = useState([]);
  const [earnings, setEarnings] = useState(null);
  const [busy, setBusy] = useState(false);
  const [slot, setSlot] = useState({ weekday: "0", start: "09:00", end: "17:00" });

  const load = useCallback(async () => {
    try {
      const [m, i, a, e] = await Promise.all([
        api.get("/doctor/me"), api.get("/consults/inbox"),
        api.get("/doctor/availability"), api.get("/doctor/earnings"),
      ]);
      setMe(m.data); setInbox(i.data); setSlots(a.data); setEarnings(e.data);
    } catch (e) {
      if (e?.response?.status === 403) navigate("/doctor/apply");
      else toast.error("Couldn't load your dashboard");
    }
  }, [navigate]);

  useEffect(() => { load(); }, [load]);

  // Poll the inbox so a "talk now" request shows up without a refresh, and keep the
  // presence heartbeat alive — the server marks a doctor offline without one.
  useEffect(() => {
    const inboxTimer = setInterval(() => {
      api.get("/consults/inbox").then(({ data }) => setInbox(data)).catch(() => {});
    }, 10000);
    return () => clearInterval(inboxTimer);
  }, []);

  useEffect(() => {
    if (!me?.is_online) return undefined;
    const beat = setInterval(() => { api.post("/doctor/heartbeat").catch(() => {}); }, HEARTBEAT_MS);
    return () => clearInterval(beat);
  }, [me?.is_online]);

  const toggleOnline = async (on) => {
    setMe((m) => ({ ...m, is_online: on }));
    try {
      await api.put("/doctor/online", { is_online: on });
      toast.success(on ? "You're online — people can reach you now." : "You're offline.");
    } catch {
      setMe((m) => ({ ...m, is_online: !on }));
      toast.error("Couldn't change your status");
    }
  };

  const accept = async (id) => {
    setBusy(true);
    try {
      await api.post(`/consults/${id}/accept`);
      navigate(`/consult/${id}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't accept");
      load();
    } finally { setBusy(false); }
  };

  const addSlot = async () => {
    if (slot.start >= slot.end) return toast.error("End time must be after start time");
    try {
      const { data } = await api.post("/doctor/availability", {
        weekday: parseInt(slot.weekday, 10), start: slot.start, end: slot.end,
      });
      setSlots((s) => [...s, data]);
      toast.success("Availability added");
    } catch (e) { toast.error(e?.response?.data?.detail || "Couldn't add that"); }
  };

  const delSlot = async (id) => {
    await api.delete(`/doctor/availability/${id}`);
    setSlots((s) => s.filter((x) => x.id !== id));
  };

  const saveRate = async (price, volunteer) => {
    try {
      const { data } = await api.put("/doctor/profile", {
        is_volunteer: volunteer, session_price: volunteer ? 0 : parseFloat(price) || 0,
      });
      setMe(data);
      toast.success("Saved");
    } catch (e) { toast.error(e?.response?.data?.detail || "Couldn't save"); }
  };

  if (!me) return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  const open = inbox.filter((s) => s.status === "requested");
  const upcoming = inbox.filter((s) => s.status !== "requested");

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-6">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-10 w-10 rounded-full border border-border bg-white/[0.04] flex items-center justify-center shrink-0 overflow-hidden">
            {me.photo_path
              ? <img src={me.photo_path} alt="" className="h-full w-full object-cover" />
              : <span className="text-sm font-medium text-foreground/80">{initials(me.name)}</span>}
          </div>
          <span className="font-display font-semibold text-xl tracking-tight truncate">{me.name}</span>
          <RatingStars value={me.rating_avg} count={me.rating_count} testid="my-rating" />
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className={`text-xs ${me.is_online ? "text-emerald-400" : "text-muted-foreground"}`}>
              {me.is_online ? "Online" : "Offline"}
            </span>
            <Switch checked={!!me.is_online} onCheckedChange={toggleOnline} data-testid="online-toggle" />
          </div>
          <AccountMenu />
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Open requests", value: open.length, alert: open.length > 0 },
            { label: "Upcoming", value: upcoming.length },
            { label: "Owed to you", value: `$${earnings?.unsettled ?? 0}` },
            { label: "Paid out", value: `$${earnings?.settled ?? 0}` },
          ].map((c) => (
            <div key={c.label} className="rounded-none border border-border bg-card p-5" data-testid={`doc-stat-${c.label}`}>
              <p className={`text-3xl font-mono-data ${c.alert ? "text-emerald-400" : ""}`}>{c.value}</p>
              <p className="text-xs text-muted-foreground">{c.label}</p>
            </div>
          ))}
        </div>

        <Tabs defaultValue="sessions">
          <TabsList className="rounded-full">
            <TabsTrigger value="sessions" className="rounded-full" data-testid="doc-tab-sessions">Sessions</TabsTrigger>
            <TabsTrigger value="availability" className="rounded-full" data-testid="doc-tab-availability">Availability</TabsTrigger>
            <TabsTrigger value="earnings" className="rounded-full" data-testid="doc-tab-earnings">Earnings</TabsTrigger>
            <TabsTrigger value="profile" className="rounded-full" data-testid="doc-tab-profile">Profile</TabsTrigger>
          </TabsList>

          <TabsContent value="sessions" className="mt-6 space-y-6">
            {!me.is_online && (
              <p className="text-sm text-muted-foreground rounded-2xl border border-border bg-card/30 p-5">
                You're offline — instant requests won't reach you. Flip the switch above when you're free.
              </p>
            )}
            {open.length > 0 && (
              <div>
                <p className="text-[10px] tracking-[0.3em] uppercase text-emerald-400 mb-3 flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 soft-pulse" /> Waiting for you
                </p>
                <div className="space-y-px bg-emerald-400/20 border border-emerald-400/30 rounded-2xl overflow-hidden" data-testid="open-requests">
                  {open.map((s) => {
                    const Icon = MODE_ICON[s.mode] || Video;
                    return (
                      <div key={s.id} className="bg-card/80 p-5 flex items-center gap-4" data-testid={`request-${s.id}`}>
                        <PatientAvatar name={s.user_name} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{s.user_name}</p>
                          <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                            <Icon className="h-3 w-3" strokeWidth={1.5} /> {MODE_LABEL[s.mode] || s.mode}
                          </p>
                          {s.note && <p className="text-sm text-muted-foreground truncate mt-0.5">{s.note}</p>}
                          {s.kind === "crisis" && <span className="text-[10px] tracking-[0.15em] uppercase text-escalation">Crisis</span>}
                        </div>
                        <Button className="rounded-full bg-emerald-500 text-white hover:bg-emerald-400 shrink-0"
                          onClick={() => accept(s.id)} disabled={busy} data-testid={`accept-${s.id}`}>Accept</Button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            <div>
              <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-3">Upcoming</p>
              {upcoming.length === 0 ? (
                <p className="text-sm text-muted-foreground rounded-2xl border border-border bg-card/30 p-5" data-testid="no-upcoming">Nothing scheduled.</p>
              ) : (
                <div className="space-y-px bg-border border border-border rounded-2xl overflow-hidden">
                  {upcoming.map((s) => {
                    const Icon = MODE_ICON[s.mode] || Video;
                    return (
                      <div key={s.id} className="bg-card/60 p-5 flex items-center gap-4" data-testid={`upcoming-${s.id}`}>
                        <PatientAvatar name={s.user_name} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate">{s.user_name}</p>
                          <p className="font-mono-data text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                            <Icon className="h-3 w-3" strokeWidth={1.5} /> {fmt(s.scheduled_at || s.created_at)}
                          </p>
                        </div>
                        <span className="text-xs text-muted-foreground capitalize hidden sm:block">{s.status}</span>
                        <Button variant="outline" className="rounded-full border-border shrink-0"
                          onClick={() => navigate(`/consult/${s.id}`)} data-testid={`join-${s.id}`}>Join</Button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="availability" className="mt-6 space-y-5">
            <div className="rounded-none border border-border bg-card p-6">
              <p className="font-medium mb-4">Add a weekly slot</p>
              <div className="flex flex-wrap items-end gap-3">
                <div className="w-40">
                  <Label className="text-xs text-muted-foreground">Day</Label>
                  <Select value={slot.weekday} onValueChange={(v) => setSlot((s) => ({ ...s, weekday: v }))}>
                    <SelectTrigger className="mt-1.5 rounded-full h-10" data-testid="slot-day"><SelectValue /></SelectTrigger>
                    <SelectContent>{DAYS.map((d, i) => <SelectItem key={i} value={String(i)}>{d}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">From</Label>
                  <Input type="time" className="mt-1.5 rounded-full h-10 w-32" value={slot.start}
                    onChange={(e) => setSlot((s) => ({ ...s, start: e.target.value }))} data-testid="slot-start" />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">To</Label>
                  <Input type="time" className="mt-1.5 rounded-full h-10 w-32" value={slot.end}
                    onChange={(e) => setSlot((s) => ({ ...s, end: e.target.value }))} data-testid="slot-end" />
                </div>
                <Button className="rounded-full gap-1.5" onClick={addSlot} data-testid="slot-add"><Plus className="h-4 w-4" /> Add</Button>
              </div>
              <p className="text-xs text-muted-foreground mt-4">Times are UTC. With no slots set, people can book any time.</p>
            </div>

            {slots.length > 0 && (
              <div className="space-y-px bg-border border border-border rounded-2xl overflow-hidden" data-testid="slots-list">
                {slots.map((s) => (
                  <div key={s.id} className="bg-card/60 p-4 flex items-center gap-4 group">
                    <span className="text-sm w-28 shrink-0">{DAYS[s.weekday]}</span>
                    <span className="font-mono-data text-sm text-muted-foreground flex-1">{s.start} – {s.end}</span>
                    <button onClick={() => delSlot(s.id)} data-testid={`slot-del-${s.id}`}
                      className="text-muted-foreground hover:text-escalation opacity-0 group-hover:opacity-100 transition-opacity">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="earnings" className="mt-6 space-y-5">
            <div className="rounded-none border border-border bg-card p-6">
              <Wallet className="h-5 w-5 text-primary mb-3" strokeWidth={1.5} />
              <p className="font-display font-light text-4xl mb-1" data-testid="earnings-owed">${earnings?.unsettled ?? 0}</p>
              <p className="text-sm text-muted-foreground">Outstanding across {earnings?.sessions ?? 0} paid sessions. Payouts are sent manually — you'll hear from us.</p>
            </div>
            {earnings?.payouts?.length > 0 && (
              <div className="space-y-px bg-border border border-border rounded-2xl overflow-hidden" data-testid="payout-history">
                {earnings.payouts.map((p) => (
                  <div key={p.id} className="bg-card/60 p-4 flex items-center gap-4">
                    <span className="font-mono-data text-xs text-muted-foreground w-28 shrink-0">{fmt(p.created_at)}</span>
                    <p className="flex-1 text-sm truncate">{p.session_count} sessions{p.note ? ` · ${p.note}` : ""}</p>
                    <span className="font-display font-light text-lg">${p.amount}</span>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="profile" className="mt-6">
            <div className="rounded-none border border-border bg-card p-6 space-y-5">
              <label className="flex items-start gap-3 cursor-pointer">
                <Switch checked={!!me.is_volunteer} onCheckedChange={(v) => saveRate(me.session_price, v)} data-testid="profile-volunteer" />
                <span>
                  <span className="text-sm font-medium block">Volunteer</span>
                  <span className="text-sm text-muted-foreground">Free sessions. You're the only kind of doctor free users can reach.</span>
                </span>
              </label>
              {!me.is_volunteer && (
                <div className="max-w-xs">
                  <Label className="text-sm">Rate per session (USD)</Label>
                  <div className="flex gap-2 mt-1.5">
                    <Input type="number" min="1" step="1" className="rounded-full h-10" defaultValue={me.session_price}
                      onBlur={(e) => e.target.value !== String(me.session_price) && saveRate(e.target.value, false)}
                      data-testid="profile-price" />
                  </div>
                </div>
              )}
              <dl className="text-sm space-y-2 pt-2 border-t border-border">
                <div className="flex justify-between"><dt className="text-muted-foreground">Credentials</dt><dd>{me.credentials}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Country</dt><dd>{me.country}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Languages</dt><dd>{(me.languages || []).join(", ")}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Identity check</dt><dd className="font-mono-data">{me.kyc?.status || "—"}</dd></div>
              </dl>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
