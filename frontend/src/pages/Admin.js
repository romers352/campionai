import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, API } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useVisibilityRefetch } from "@/hooks/use-visibility-refetch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/components/ui/sonner";
import AccountMenu from "@/components/AccountMenu";
import {
  HeartHandshake, ArrowLeft, Users, MessageSquare, Brain, ShieldAlert,
  Cpu, Trash2, Plus, Search, Loader2, CheckCircle2, Volume2, Mail, Smartphone, Stethoscope, Wallet,
} from "lucide-react";

const PROVIDERS = [
  { v: "emergent-openai", l: "Emergent · OpenAI" },
  { v: "emergent-anthropic", l: "Emergent · Anthropic" },
  { v: "emergent-gemini", l: "Emergent · Gemini" },
  { v: "openrouter", l: "OpenRouter" },
];

export default function Admin() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [routes, setRoutes] = useState({});
  const [provider, setProvider] = useState({ llm_provider: "emergent", openrouter_api_key_set: false });
  const [orKey, setOrKey] = useState("");
  const [orModels, setOrModels] = useState([]);
  const [orSearch, setOrSearch] = useState("");
  const [loadingModels, setLoadingModels] = useState(false);
  const [events, setEvents] = useState([]);
  const [docs, setDocs] = useState([]);
  const [docFilter, setDocFilter] = useState("pending");
  const [pendingCount, setPendingCount] = useState(0);
  const [reasons, setReasons] = useState({});
  const [payouts, setPayouts] = useState([]);
  const [consultSettings, setConsultSettings] = useState({});
  const [voice, setVoice] = useState({ enabled: true, voice_id: "", key_set: false });
  const [fishKey, setFishKey] = useState("");
  const [integrations, setIntegrations] = useState({});

  const loadAll = async () => {
    const [s, r, pv, e, v, i, po, cs] = await Promise.all([
      api.get("/admin/stats"), api.get("/admin/model-config"), api.get("/admin/provider-settings"),
      api.get("/admin/safety-events"), api.get("/admin/voice-settings"), api.get("/admin/integrations"),
      api.get("/admin/payouts"), api.get("/admin/consult-settings"),
    ]);
    setStats(s.data); setRoutes(r.data); setProvider(pv.data); setEvents(e.data);
    setVoice(v.data); setIntegrations(i.data); setPayouts(po.data); setConsultSettings(cs.data);
  };

  const loadDoctors = useCallback(async () => {
    const [list, pending] = await Promise.all([
      api.get("/admin/doctors", { params: { status: docFilter || undefined } }),
      api.get("/admin/doctors", { params: { status: "pending" } }),
    ]);
    setDocs(list.data);
    setPendingCount(pending.data.length);
  }, [docFilter]);

  useEffect(() => { loadAll(); }, []);
  useEffect(() => { loadDoctors(); }, [loadDoctors]);

  // Licence documents are served through the authenticated file route.
  const fileUrl = (path) => `${API}/files/${path}?auth=${localStorage.getItem("campion_token")}`;

  const setDoctorStatus = async (id, status) => {
    try {
      await api.put(`/admin/doctors/${id}/status`, { status, reason: reasons[id] || undefined });
      toast.success(`Doctor ${status}`);
      setReasons((r) => ({ ...r, [id]: "" }));
      loadDoctors();
      loadAll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Couldn't update");
    }
  };

  const saveConsultSettings = async () => {
    try {
      const { data } = await api.put("/admin/consult-settings", {
        commission_pct: parseFloat(consultSettings.commission_pct) || 0,
        free_volunteer_sessions_per_month: parseInt(consultSettings.free_volunteer_sessions_per_month, 10) || 0,
      });
      setConsultSettings(data);
      toast.success("Consult settings saved");
    } catch (e) { toast.error(e?.response?.data?.detail || "Couldn't save"); }
  };

  const settle = async (doctor_id) => {
    try {
      const { data } = await api.post("/admin/payouts/settle", { doctor_id });
      toast.success(`Marked $${data.amount} settled`);
      loadAll();
    } catch (e) { toast.error(e?.response?.data?.detail || "Couldn't settle"); }
  };

  // Keep admin dashboards (stats, professionals, safety events) fresh on refocus.
  useVisibilityRefetch(() => { loadAll().catch(() => {}); });

  const saveVoice = async () => {
    await api.put("/admin/voice-settings", { enabled: voice.enabled, voice_id: voice.voice_id, fish_audio_api_key: fishKey || undefined });
    toast.success("Voice settings saved");
    setFishKey("");
    loadAll();
  };

  const saveRoute = async (tier, field, value) => {
    const updated = { ...routes[tier], [field]: value };
    setRoutes((r) => ({ ...r, [tier]: updated }));
    await api.put("/admin/model-config", { tier, provider: updated.provider, model: updated.model });
    toast.success(`${tier} model updated`);
  };

  const saveProvider = async () => {
    await api.put("/admin/provider-settings", { llm_provider: provider.llm_provider, openrouter_api_key: orKey || undefined });
    toast.success("Provider settings saved");
    setOrKey("");
    loadAll();
  };

  const loadOrModels = async () => {
    setLoadingModels(true);
    try {
      const { data } = await api.get("/admin/openrouter-models");
      setOrModels(data.models);
      toast.success(`${data.models.length} OpenRouter models loaded`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Add an OpenRouter key first");
    } finally {
      setLoadingModels(false);
    }
  };

  const resolveEvent = async (id) => {
    await api.put(`/admin/safety-events/${id}/resolve`);
    setEvents((ev) => ev.map((e) => e.id === id ? { ...e, resolved: true } : e));
    toast.success("Marked resolved");
  };

  const filteredModels = orModels.filter((m) => m.id.toLowerCase().includes(orSearch.toLowerCase())).slice(0, 40);

  const statCards = stats ? [
    { icon: Users, label: "Users", value: stats.users },
    { icon: MessageSquare, label: "Messages", value: stats.messages },
    { icon: Brain, label: "Memories", value: stats.memories },
    { icon: Stethoscope, label: "Verified doctors", value: stats.doctors },
    { icon: ShieldAlert, label: "Open safety events", value: stats.open_safety_events, alert: stats.open_safety_events > 0 },
  ] : [];

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate("/chat")} data-testid="admin-back-button">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
              <HeartHandshake className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-display font-extrabold">CampionAI · Admin</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="rounded-full hidden sm:inline-flex">{user?.email}</Badge>
          <AccountMenu />
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {statCards.map((c) => (
            <div key={c.label} className="rounded-none border border-border bg-card p-5" data-testid={`stat-${c.label}`}>
              <c.icon className={`h-5 w-5 mb-3 ${c.alert ? "text-escalation" : "text-primary"}`} />
              <p className="text-3xl font-mono-data">{c.value}</p>
              <p className="text-xs text-muted-foreground">{c.label}</p>
            </div>
          ))}
        </div>

        <Tabs defaultValue="models">
          <TabsList className="rounded-full">
            <TabsTrigger value="models" className="rounded-full" data-testid="admin-tab-models">Models & routing</TabsTrigger>
            <TabsTrigger value="doctors" className="rounded-full" data-testid="admin-tab-doctors">Doctors</TabsTrigger>
            <TabsTrigger value="payouts" className="rounded-full" data-testid="admin-tab-payouts">Payouts</TabsTrigger>
            <TabsTrigger value="safety" className="rounded-full" data-testid="admin-tab-safety">Safety events</TabsTrigger>
            <TabsTrigger value="voice" className="rounded-full" data-testid="admin-tab-voice">Voice & alerts</TabsTrigger>
          </TabsList>

          {/* MODELS */}
          <TabsContent value="models" className="mt-6 space-y-6">
            <div className="rounded-none border border-border bg-card p-6">
              <h3 className="font-display font-bold mb-1 flex items-center gap-2"><Cpu className="h-4 w-4 text-primary" /> Model routing</h3>
              <p className="text-sm text-muted-foreground mb-5">Route each task tier to a model. Safety uncertainty always escalates to the powerful tier.</p>
              <div className="space-y-4">
                {["cheap", "medium", "powerful"].map((tier) => (
                  <div key={tier} className="grid grid-cols-1 md:grid-cols-[120px_1fr_1fr] gap-3 items-center" data-testid={`route-${tier}`}>
                    <Label className="capitalize font-medium">{tier}</Label>
                    <Select value={routes[tier]?.provider} onValueChange={(v) => saveRoute(tier, "provider", v)}>
                      <SelectTrigger className="rounded-full h-10" data-testid={`route-provider-${tier}`}><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {PROVIDERS.map((p) => <SelectItem key={p.v} value={p.v}>{p.l}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Input className="rounded-full h-10" value={routes[tier]?.model || ""} data-testid={`route-model-${tier}`}
                      onChange={(e) => setRoutes((r) => ({ ...r, [tier]: { ...r[tier], model: e.target.value } }))}
                      onBlur={(e) => saveRoute(tier, "model", e.target.value)}
                      placeholder="model id" />
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-none border border-border bg-card p-6">
              <h3 className="font-display font-bold mb-1">OpenRouter</h3>
              <p className="text-sm text-muted-foreground mb-5">Use your own OpenRouter key to unlock hundreds of models. Set a tier's provider to "OpenRouter" and paste any model id above.</p>
              <div className="flex flex-col md:flex-row gap-3 mb-4">
                <Select value={provider.llm_provider} onValueChange={(v) => setProvider((p) => ({ ...p, llm_provider: v }))}>
                  <SelectTrigger className="rounded-full h-10 md:w-56" data-testid="provider-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="emergent">Default (Emergent key)</SelectItem>
                    <SelectItem value="openrouter">OpenRouter (all tiers)</SelectItem>
                  </SelectContent>
                </Select>
                <Input className="rounded-full h-10 flex-1" type="password" placeholder={provider.openrouter_api_key_set ? "•••• key saved — paste to replace" : "sk-or-..."}
                  value={orKey} onChange={(e) => setOrKey(e.target.value)} data-testid="openrouter-key-input" />
                <Button className="rounded-full" onClick={saveProvider} data-testid="save-provider-button">Save</Button>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" className="rounded-full" onClick={loadOrModels} disabled={loadingModels} data-testid="load-models-button">
                  {loadingModels ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : <Search className="h-4 w-4 mr-1.5" />} Load available models
                </Button>
              </div>
              {orModels.length > 0 && (
                <div className="mt-4">
                  <div className="relative mb-3">
                    <Search className="h-4 w-4 absolute left-3 top-3 text-muted-foreground" />
                    <Input className="rounded-full h-10 pl-9" placeholder="Search models…" value={orSearch} onChange={(e) => setOrSearch(e.target.value)} data-testid="model-search-input" />
                  </div>
                  <div className="max-h-64 overflow-y-auto space-y-1.5">
                    {filteredModels.map((m) => (
                      <div key={m.id} className="flex items-center justify-between rounded-xl border border-border px-3 py-2" data-testid={`or-model-${m.id}`}>
                        <div className="min-w-0"><p className="text-sm truncate">{m.name}</p><p className="text-xs text-muted-foreground truncate">{m.id}</p></div>
                        <Button size="sm" variant="ghost" className="rounded-full shrink-0" onClick={() => { navigator.clipboard?.writeText(m.id); toast.success(`Copied ${m.id}`); }}>Copy id</Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {/* DOCTORS */}
          <TabsContent value="doctors" className="mt-6 space-y-5">
            <div className="flex gap-2">
              {[["pending", "Pending"], ["verified", "Verified"], ["rejected", "Rejected"], ["suspended", "Suspended"], ["", "All"]].map(([v, l]) => (
                <Button key={v || "all"} variant={docFilter === v ? "default" : "outline"} className="rounded-full h-9"
                  onClick={() => setDocFilter(v)} data-testid={`doc-filter-${v || "all"}`}>
                  {l}{v === "pending" && pendingCount > 0 ? ` (${pendingCount})` : ""}
                </Button>
              ))}
            </div>

            {docs.length === 0 && <p className="text-sm text-muted-foreground py-10 text-center" data-testid="no-doctors">No doctors here.</p>}

            <div className="space-y-3">
              {docs.map((d) => (
                <div key={d.id} className="rounded-none border border-border bg-card p-5" data-testid={`admin-doctor-${d.id}`}>
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="min-w-0">
                      <p className="font-medium">
                        {d.name} <span className="text-xs text-muted-foreground">· {d.credentials}</span>
                        {d.is_volunteer && <span className="ml-2 text-[10px] tracking-[0.15em] uppercase border border-border px-2 py-0.5 rounded-full text-muted-foreground">Volunteer</span>}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {d.email} · {d.country} · {(d.languages || []).join(", ")} · {d.session_price > 0 ? `$${d.session_price}/session` : "Free"}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Licence <span className="font-mono-data">{d.licence_number}</span> ·
                        Identity <span className={`font-mono-data ${d.kyc?.status === "approved" ? "text-primary" : d.kyc?.status === "declined" ? "text-escalation" : ""}`}>
                          {d.kyc?.status || "not started"}
                        </span>
                      </p>
                      {d.bio && <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{d.bio}</p>}
                      {d.review_reason && <p className="text-xs text-muted-foreground mt-2 border-l-2 border-border pl-3">{d.review_reason}</p>}
                    </div>
                    <span className={`text-[10px] tracking-[0.15em] uppercase px-2 py-1 border shrink-0 ${d.status === "verified" ? "border-primary text-primary" : d.status === "pending" ? "border-border text-muted-foreground" : "border-escalation/40 text-escalation"}`}>
                      {d.status}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {d.licence_doc_path && (
                      <a href={fileUrl(d.licence_doc_path)} target="_blank" rel="noopener noreferrer"
                        className="text-xs underline text-muted-foreground hover:text-foreground" data-testid={`licence-${d.id}`}>
                        View licence document
                      </a>
                    )}
                    <div className="flex-1" />
                    <Input className="rounded-full h-9 w-56" placeholder="Reason (required to override)"
                      value={reasons[d.id] || ""} data-testid={`reason-${d.id}`}
                      onChange={(e) => setReasons((r) => ({ ...r, [d.id]: e.target.value }))} />
                    {d.status !== "verified" && (
                      <Button className="rounded-full h-9" onClick={() => setDoctorStatus(d.id, "verified")} data-testid={`approve-${d.id}`}>
                        Approve
                      </Button>
                    )}
                    {d.status !== "rejected" && (
                      <Button variant="outline" className="rounded-full h-9 border-escalation/40 text-escalation hover:bg-escalation/10"
                        onClick={() => setDoctorStatus(d.id, "rejected")} data-testid={`reject-${d.id}`}>
                        Reject
                      </Button>
                    )}
                    {d.status === "verified" && (
                      <Button variant="outline" className="rounded-full h-9 border-border"
                        onClick={() => setDoctorStatus(d.id, "suspended")} data-testid={`suspend-${d.id}`}>
                        Suspend
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* PAYOUTS */}
          <TabsContent value="payouts" className="mt-6 space-y-5">
            <div className="rounded-none border border-border bg-card p-6">
              <h3 className="font-display font-bold mb-1 flex items-center gap-2"><Wallet className="h-4 w-4 text-primary" /> Consult settings</h3>
              <p className="text-sm text-muted-foreground mb-5">Commission is taken from every paid session. The free cap applies to volunteer sessions only — crisis sessions are never counted.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs text-muted-foreground">Commission %</Label>
                  <Input type="number" min="0" max="100" step="1" className="rounded-full h-10 mt-1.5" data-testid="commission-input"
                    value={consultSettings.commission_pct ?? ""}
                    onChange={(e) => setConsultSettings((s) => ({ ...s, commission_pct: e.target.value }))} />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Free volunteer sessions / month</Label>
                  <Input type="number" min="0" max="100" step="1" className="rounded-full h-10 mt-1.5" data-testid="freecap-input"
                    value={consultSettings.free_volunteer_sessions_per_month ?? ""}
                    onChange={(e) => setConsultSettings((s) => ({ ...s, free_volunteer_sessions_per_month: e.target.value }))} />
                </div>
              </div>
              <Button className="rounded-full mt-4" onClick={saveConsultSettings} data-testid="save-consult-settings">Save</Button>
            </div>

            <div className="rounded-none border border-border bg-card p-6">
              <h3 className="font-display font-bold mb-1">Outstanding payouts</h3>
              <p className="text-sm text-muted-foreground mb-5">Send the money off-platform, then mark it settled here.</p>
              {payouts.length === 0 ? (
                <p className="text-sm text-muted-foreground py-6 text-center" data-testid="no-payouts">Nothing outstanding.</p>
              ) : (
                <div className="space-y-2" data-testid="payouts-list">
                  {payouts.map((p) => (
                    <div key={p.doctor_id} className="flex items-center gap-4 border border-border p-4" data-testid={`payout-${p.doctor_id}`}>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{p.name}</p>
                        <p className="text-xs text-muted-foreground truncate">{p.email} · {p.country} · {p.sessions} sessions · ${p.commission} commission</p>
                      </div>
                      <span className="font-display font-light text-2xl shrink-0">${p.owed}</span>
                      <Button className="rounded-full shrink-0" onClick={() => settle(p.doctor_id)} data-testid={`settle-${p.doctor_id}`}>
                        Mark settled
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          {/* SAFETY */}
          <TabsContent value="safety" className="mt-6 space-y-2">
            {events.length === 0 && <p className="text-sm text-muted-foreground py-10 text-center">No safety events yet.</p>}
            {events.map((e) => (
              <div key={e.id} className="rounded-none border border-border bg-card p-4" data-testid={`event-${e.id}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Badge className={`rounded-full ${e.risk_level === "high" ? "bg-escalation" : "bg-primary"}`}>{e.risk_level}</Badge>
                    <span className="text-sm font-medium">{e.user_email}</span>
                  </div>
                  {e.resolved ? <Badge variant="secondary" className="rounded-full">Resolved</Badge> :
                    <Button size="sm" variant="outline" className="rounded-full" onClick={() => resolveEvent(e.id)} data-testid={`resolve-${e.id}`}>Mark resolved</Button>}
                </div>
                <p className="text-sm text-muted-foreground italic">"{e.trigger_text}"</p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {(e.actions_taken || []).map((a, i) => <Badge key={i} variant="secondary" className="rounded-full text-[10px]">{a}</Badge>)}
                </div>
                <p className="text-[11px] text-muted-foreground mt-2 font-mono-data">{new Date(e.created_at).toLocaleString()}</p>
              </div>
            ))}
          </TabsContent>

          {/* VOICE & ALERTS */}
          <TabsContent value="voice" className="mt-6 space-y-6">
            <div className="rounded-none border border-border bg-card p-6">
              <h3 className="font-display font-bold mb-1 flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-escalation" /> Alert delivery</h3>
              <p className="text-sm text-muted-foreground mb-5">Real escalation alerts to trusted contacts & professionals. Add keys to backend .env to enable.</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-px bg-border">
                {[
                  { icon: Mail, label: "Email (Resend)", on: integrations.email_resend, key: "email" },
                  { icon: Smartphone, label: "SMS (Twilio)", on: integrations.sms_twilio, key: "sms" },
                  { icon: Volume2, label: "Voice (Fish Audio)", on: integrations.voice_fish, key: "voice" },
                ].map((it) => (
                  <div key={it.key} className="bg-card p-4 flex items-center gap-3" data-testid={`integration-${it.key}`}>
                    <it.icon className="h-4 w-4 text-muted-foreground" />
                    <div className="flex-1">
                      <p className="text-sm">{it.label}</p>
                      <p className={`text-[11px] font-mono-data ${it.on ? "text-emerald-400" : "text-muted-foreground"}`}>{it.on ? "CONFIGURED" : "not configured"}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-none border border-border bg-card p-6">
              <h3 className="font-display font-bold mb-1 flex items-center gap-2"><Volume2 className="h-4 w-4 text-primary" /> Voice (Fish Audio)</h3>
              <p className="text-sm text-muted-foreground mb-5">Bring your own Fish Audio key so CampionAI can speak. Speech-to-text runs in the browser, no key needed.</p>
              <div className="flex items-center justify-between border border-border p-4 mb-4">
                <div>
                  <p className="text-sm font-medium">Enable voice replies</p>
                  <p className="text-xs text-muted-foreground">Users get a speaker toggle in chat.</p>
                </div>
                <Switch data-testid="voice-enabled-toggle" checked={voice.enabled} onCheckedChange={(v) => setVoice((s) => ({ ...s, enabled: v }))} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Input className="rounded-none h-10" type="password" placeholder={voice.key_set ? "•••• key saved — paste to replace" : "Fish Audio API key"} value={fishKey} onChange={(e) => setFishKey(e.target.value)} data-testid="fish-key-input" />
                <Input className="rounded-none h-10" placeholder="Reference voice id (optional)" value={voice.voice_id || ""} onChange={(e) => setVoice((s) => ({ ...s, voice_id: e.target.value }))} data-testid="fish-voice-id-input" />
              </div>
              <Button className="rounded-none mt-4 bg-primary text-primary-foreground hover:bg-zinc-200" onClick={saveVoice} data-testid="save-voice-button">Save voice settings</Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
