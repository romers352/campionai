import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/sonner";
import { Trash2, Brain, Lock, Loader2 } from "lucide-react";

const TIER_LABEL = { LONG_TERM: "Long-term", SESSION: "This period", TEMPORARY: "Temporary" };

export default function MemoryDrawer({ open, onOpenChange }) {
  const { user, setUser } = useAuth();
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [privateMode, setPrivateMode] = useState(user?.private_mode || false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/memories");
      setMemories(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (open) load(); }, [open]);
  useEffect(() => { setPrivateMode(user?.private_mode || false); }, [user]);

  const del = async (id) => {
    await api.delete(`/memories/${id}`);
    setMemories((m) => m.filter((x) => x.id !== id));
    toast.success("Forgotten");
  };

  const togglePrivate = async (v) => {
    setPrivateMode(v);
    await api.put("/settings/private-mode", { enabled: v });
    setUser((u) => ({ ...u, private_mode: v }));
    toast(v ? "Private Mode on — this session won't be remembered" : "Private Mode off");
  };

  const grouped = memories.reduce((acc, m) => {
    (acc[m.tier] = acc[m.tier] || []).push(m);
    return acc;
  }, {});

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-md overflow-y-auto" data-testid="memory-drawer">
        <SheetHeader>
          <SheetTitle className="font-display flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" /> Memory
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 rounded-2xl border border-border/60 p-4 flex items-center justify-between">
          <div className="flex items-start gap-3">
            <div className="h-9 w-9 rounded-full bg-primary/12 flex items-center justify-center">
              <Lock className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium">Private Mode</p>
              <p className="text-xs text-muted-foreground max-w-[210px]">Session-only. Nothing is remembered long-term.</p>
            </div>
          </div>
          <Switch data-testid="private-mode-toggle" checked={privateMode} onCheckedChange={togglePrivate} />
        </div>

        <div className="mt-6">
          {loading ? (
            <div className="flex justify-center py-10"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>
          ) : memories.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-10">
              Nothing remembered yet. As we talk, I'll gently hold onto what matters — and you can edit or forget anything here.
            </p>
          ) : (
            Object.keys(grouped).sort().map((tier) => (
              <div key={tier} className="mb-6">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">{TIER_LABEL[tier] || tier}</p>
                <div className="space-y-2">
                  {grouped[tier].map((m) => (
                    <div key={m.id} className="group flex items-start justify-between gap-3 rounded-2xl border border-border/60 p-3.5" data-testid={`memory-item-${m.id}`}>
                      <div>
                        <p className="text-sm leading-snug">{m.content}</p>
                        <Badge variant="secondary" className="mt-1.5 text-[10px] rounded-full capitalize">{m.category}</Badge>
                      </div>
                      <button data-testid={`forget-memory-${m.id}`} onClick={() => del(m.id)}
                        className="text-muted-foreground hover:text-escalation transition-colors opacity-0 group-hover:opacity-100 shrink-0">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
