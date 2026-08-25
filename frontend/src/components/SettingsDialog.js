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
import { Download, Loader2 } from "lucide-react";

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
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const toList = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

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
          <TabsList className="grid grid-cols-2 rounded-full">
            <TabsTrigger value="profile" className="rounded-full" data-testid="tab-profile">Profile</TabsTrigger>
            <TabsTrigger value="data" className="rounded-full" data-testid="tab-data">Data & privacy</TabsTrigger>
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

          <TabsContent value="data" className="space-y-3 mt-4">
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
