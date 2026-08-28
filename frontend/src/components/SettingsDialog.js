import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { toast } from "@/components/ui/sonner";
import { getTheme, applyTheme } from "@/lib/theme";
import { Download, Loader2, Moon, Sun, Printer, Heart, Sparkles } from "lucide-react";

const TONES = [
  { id: "gentle", label: "Gentle & soft", desc: "Slow, soothing, tender" },
  { id: "warm", label: "Warm & balanced", desc: "The caring close friend" },
  { id: "direct", label: "Direct & honest", desc: "Clear and to the point, still kind" },
  { id: "playful", label: "Playful & light", desc: "A little humour and buoyancy" },
];

export default function SettingsDialog({ open, onOpenChange }) {
  const { user, refresh, logout } = useAuth();
  const navigate = useNavigate();
  const p = user?.profile || {};
  const [form, setForm] = useState({
    preferred_name: p.preferred_name || "",
    work: p.work || "",
    education: p.education || "",
    goals: (p.goals || []).join(", "),
    likes: (p.likes || []).join(", "),
    important_people: (p.important_people || []).join(", "),
  });
  const [saving, setSaving] = useState(false);
  const [theme, setTheme] = useState(getTheme());
  const [tone, setTone] = useState(p.communication_style || "warm");
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const toList = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

  const switchTheme = (t) => { setTheme(t); applyTheme(t); };

  const pickTone = async (id) => {
    setTone(id);
    try {
      await api.put("/profile", { communication_style: id });
      await refresh();
      toast.success("Got it — I'll talk that way from now on");
    } catch { toast.error("Couldn't save that"); }
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/profile", {
        preferred_name: form.preferred_name,
        work: form.work,
        education: form.education,
        goals: toList(form.goals),
        likes: toList(form.likes),
        important_people: toList(form.important_people),
      });
      await refresh();
      toast.success("Profile updated");
    } finally {
      setSaving(false);
    }
  };

  const exportData = async () => {
    const { data } = await api.get("/data/export");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "campionai-my-data.json"; a.click();
    URL.revokeObjectURL(url);
    toast.success("Your data has been exported");
  };

  const printKeepsake = async () => {
    const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
    try {
      const { data } = await api.get("/data/export");
      const name = data.profile?.profile?.preferred_name || "friend";
      const st = data.stats || {};
      const moods = (data.mood_journal || []).map((m) => `<tr><td>${esc(m.date)}</td><td>${esc(m.mood)}/5</td><td>${esc(m.note)}</td></tr>`).join("");
      const grat = (data.gratitude || []).map((g) => `<li>${esc(g.text)}</li>`).join("");
      const mems = (data.memories || []).slice(0, 100).map((m) => `<li>${esc(m.text)}</li>`).join("");
      const w = window.open("", "_blank");
      if (!w) return toast.error("Allow pop-ups to open the keepsake");
      w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>CampionAI — a keepsake for ${esc(name)}</title>
        <style>
          body{font-family:Georgia,serif;color:#1a1a1c;max-width:720px;margin:40px auto;padding:0 24px;line-height:1.7}
          h1{font-weight:400;font-size:34px;margin-bottom:4px}h2{font-weight:400;border-bottom:1px solid #eee;padding-bottom:6px;margin-top:40px}
          .sub{color:#888;margin-top:0}.stats{display:flex;gap:24px;flex-wrap:wrap;margin:20px 0}
          .stat{text-align:center}.stat b{display:block;font-size:26px}.stat span{color:#888;font-size:12px;text-transform:uppercase;letter-spacing:.1em}
          table{width:100%;border-collapse:collapse;font-family:system-ui,sans-serif;font-size:14px}td{padding:6px 8px;border-bottom:1px solid #f0f0f0}
          ul{font-family:system-ui,sans-serif;font-size:14px}.print{margin:24px 0;padding:10px 18px;border:1px solid #1a1a1c;border-radius:999px;background:#1a1a1c;color:#fff;cursor:pointer}
          @media print{.print{display:none}}
        </style></head><body>
        <h1>A little keepsake, ${esc(name)}.</h1>
        <p class="sub">From CampionAI · ${esc((data.exported_at || "").slice(0, 10))}</p>
        <button class="print" onclick="window.print()">Save as PDF / Print</button>
        <div class="stats">
          <div class="stat"><b>${esc(st.conversations || 0)}</b><span>Conversations</span></div>
          <div class="stat"><b>${esc(st.messages || 0)}</b><span>Messages</span></div>
          <div class="stat"><b>${esc(st.moods_logged || 0)}</b><span>Moods logged</span></div>
          <div class="stat"><b>${esc(st.gratitude_notes || 0)}</b><span>Gratitudes</span></div>
        </div>
        ${grat ? `<h2>Your gratitude jar</h2><ul>${grat}</ul>` : ""}
        ${moods ? `<h2>Your mood journal</h2><table>${moods}</table>` : ""}
        ${mems ? `<h2>What I remember about you</h2><ul>${mems}</ul>` : ""}
        <p style="color:#aaa;margin-top:48px;font-size:12px;font-family:system-ui,sans-serif">This is yours to keep. — CampionAI</p>
        </body></html>`);
      w.document.close();
    } catch { toast.error("Couldn't build your keepsake"); }
  };

  const deleteEverything = async () => {
    await api.delete("/data/delete-everything");
    toast.success("Everything deleted. Take care of yourself.");
    logout();
    navigate("/");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md" data-testid="settings-dialog">
        <DialogHeader><DialogTitle className="font-display">Your space</DialogTitle></DialogHeader>
        <Tabs defaultValue="profile">
          <TabsList className="grid grid-cols-3 rounded-full">
            <TabsTrigger value="profile" className="rounded-full" data-testid="tab-profile">Profile</TabsTrigger>
            <TabsTrigger value="feel" className="rounded-full" data-testid="tab-feel">Feel</TabsTrigger>
            <TabsTrigger value="data" className="rounded-full" data-testid="tab-data">Data</TabsTrigger>
          </TabsList>

          <TabsContent value="profile" className="space-y-3 mt-4 max-h-[55vh] overflow-y-auto pr-1">
            {[["preferred_name", "Preferred name"], ["work", "Work"], ["education", "Education"],
              ["goals", "Goals (comma separated)"], ["likes", "Likes (comma separated)"], ["important_people", "Important people (comma separated)"]].map(([k, l]) => (
              <div key={k}>
                <Label className="text-sm">{l}</Label>
                <Input data-testid={`settings-${k}`} className="mt-1.5 rounded-full h-10" value={form[k]} onChange={(e) => set(k, e.target.value)} />
              </div>
            ))}
            <Button onClick={save} disabled={saving} className="w-full rounded-full mt-2" data-testid="settings-save-button">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save changes"}
            </Button>
          </TabsContent>

          <TabsContent value="feel" className="space-y-6 mt-4 max-h-[55vh] overflow-y-auto pr-1">
            <div>
              <Label className="text-sm flex items-center gap-2 mb-3"><Sparkles className="h-4 w-4 text-muted-foreground" /> How should CampionAI talk to you?</Label>
              <div className="grid grid-cols-2 gap-2" data-testid="tone-picker">
                {TONES.map((t) => (
                  <button key={t.id} onClick={() => pickTone(t.id)} data-testid={`tone-${t.id}`}
                    className={`rounded-2xl border p-3 text-left transition-all ${tone === t.id ? "border-foreground bg-accent" : "border-border hover:border-foreground/40"}`}>
                    <p className="text-sm font-medium">{t.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{t.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <Label className="text-sm flex items-center gap-2 mb-3"><Moon className="h-4 w-4 text-muted-foreground" /> Appearance</Label>
              <div className="grid grid-cols-2 gap-2" data-testid="theme-picker">
                <button onClick={() => switchTheme("dark")} data-testid="theme-dark"
                  className={`rounded-2xl border p-3 flex items-center gap-3 transition-all ${theme === "dark" ? "border-foreground bg-accent" : "border-border hover:border-foreground/40"}`}>
                  <Moon className="h-4 w-4" /> <span className="text-sm">Obsidian</span>
                </button>
                <button onClick={() => switchTheme("light")} data-testid="theme-light"
                  className={`rounded-2xl border p-3 flex items-center gap-3 transition-all ${theme === "light" ? "border-foreground bg-accent" : "border-border hover:border-foreground/40"}`}>
                  <Sun className="h-4 w-4" /> <span className="text-sm">Warm light</span>
                </button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="data" className="space-y-3 mt-4">
            <button onClick={printKeepsake} data-testid="keepsake-button"
              className="w-full flex items-center gap-3 rounded-2xl border border-border/60 p-4 hover:bg-accent transition-colors text-left">
              <Heart className="h-5 w-5 text-primary" />
              <div><p className="text-sm font-medium">Create a keepsake</p><p className="text-xs text-muted-foreground">A printable memento of your journey (save as PDF)</p></div>
            </button>
            <button onClick={exportData} data-testid="export-data-button"
              className="w-full flex items-center gap-3 rounded-2xl border border-border/60 p-4 hover:bg-accent transition-colors text-left">
              <Download className="h-5 w-5 text-primary" />
              <div><p className="text-sm font-medium">Export my data</p><p className="text-xs text-muted-foreground">Download everything as JSON</p></div>
            </button>

            {/* Sign out lives in AccountMenu — one logout control, reachable from every page. */}

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <button data-testid="delete-everything-button"
                  className="w-full flex items-center gap-3 rounded-2xl border border-escalation/30 bg-escalation/5 p-4 hover:bg-escalation/10 transition-colors text-left">
                  <div><p className="text-sm font-medium text-escalation">Delete everything</p><p className="text-xs text-muted-foreground">Erase your account and all memories permanently</p></div>
                </button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete everything?</AlertDialogTitle>
                  <AlertDialogDescription>This permanently erases your account, conversations, and every memory. This cannot be undone.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel className="rounded-full" data-testid="cancel-delete-everything">Keep my data</AlertDialogCancel>
                  <AlertDialogAction onClick={deleteEverything} data-testid="confirm-delete-everything" className="rounded-full bg-escalation hover:bg-escalation/90">Delete forever</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
