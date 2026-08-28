import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
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
import {
  HeartHandshake, ArrowLeft, Users, MessageSquare, Brain, ShieldAlert,
  Cpu, Trash2, Plus, Search, Loader2, CheckCircle2, Volume2, Mail, Smartphone,
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
  const [pros, setPros] = useState([]);
  const [events, setEvents] = useState([]);
  const [newPro, setNewPro] = useState({ name: "", credentials: "", specialty: "", contact: "", availability: "on-call" });
  const [voice, setVoice] = useState({ enabled: true, voice_id: "", key_set: false });
  const [fishKey, setFishKey] = useState("");
  const [integrations, setIntegrations] = useState({});

  const loadAll = async () => {
    const [s, r, pv, p, e, v, i] = await Promise.all([
      api.get("/admin/stats"), api.get("/admin/model-config"), api.get("/admin/provider-settings"),
      api.get("/admin/professionals"), api.get("/admin/safety-events"),
      api.get("/admin/voice-settings"), api.get("/admin/integrations"),
    ]);
    setStats(s.data); setRoutes(r.data); setProvider(pv.data); setPros(p.data); setEvents(e.data);
    setVoice(v.data); setIntegrations(i.data);
  };

  useEffect(() => { loadAll(); }, []);

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

  const addPro = async () => {
    if (!newPro.name || !newPro.credentials) return toast.error("Name and credentials required");
    const { data } = await api.post("/admin/professionals", { ...newPro, verified: true });
    setPros((p) => [data, ...p]);
    setNewPro({ name: "", credentials: "", specialty: "", contact: "", availability: "on-call" });
    toast.success("Professional added");
  };

  const delPro = async (id) => {
    await api.delete(`/admin/professionals/${id}`);
    setPros((p) => p.filter((x) => x.id !== id));
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
        <Badge variant="secondary" className="rounded-full">{user?.email}</Badge>
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
            <TabsTrigger value="professionals" className="rounded-full" data-testid="admin-tab-pros">Professionals</TabsTrigger>
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

          {/* PROFESSIONALS */}
          <TabsContent value="professionals" className="mt-6 space-y-5">
            <div className="rounded-none border border-border bg-card p-6">
              <h3 className="font-display font-bold mb-4 flex items-center gap-2"><Plus className="h-4 w-4 text-primary" /> Add verified professional</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {[["name", "Full name"], ["credentials", "Credentials (e.g. PsyD)"], ["specialty", "Specialty"], ["contact", "Contact"]].map(([k, l]) => (
                  <Input key={k} className="rounded-full h-10" placeholder={l} value={newPro[k]} data-testid={`pro-${k}-input`}
                    onChange={(e) => setNewPro((p) => ({ ...p, [k]: e.target.value }))} />
                ))}
              </div>
              <Button className="rounded-full mt-4" onClick={addPro} data-testid="add-pro-button">Add professional</Button>
            </div>
            <div className="space-y-2">
              {pros.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-none border border-border bg-card p-4" data-testid={`pro-item-${p.id}`}>
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-primary" />
                    <div>
                      <p className="text-sm font-medium">{p.name} <span className="text-xs text-muted-foreground">· {p.credentials}</span></p>
                      <p className="text-xs text-muted-foreground">{p.specialty} · {p.contact}</p>
                    </div>
                  </div>
                  <button onClick={() => delPro(p.id)} className="text-muted-foreground hover:text-escalation transition-colors" data-testid={`del-pro-${p.id}`}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
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
