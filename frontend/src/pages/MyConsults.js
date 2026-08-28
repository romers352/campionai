import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import AccountMenu from "@/components/AccountMenu";
import { ArrowLeft, Loader2, Video, Phone, MessageSquare, Stethoscope } from "lucide-react";

const MODE_ICON = { video: Video, audio: Phone, chat: MessageSquare };

// Which statuses you can still walk into, versus ones that are over.
const JOINABLE = ["scheduled", "accepted", "live", "requested"];
const STATUS_LABEL = {
  requested: "Waiting for a doctor", pending_payment: "Payment needed",
  scheduled: "Scheduled", accepted: "Accepted", live: "In progress",
  completed: "Completed", cancelled: "Cancelled", expired: "Expired", no_show: "Missed",
};

const fmt = (iso) => {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
  catch { return ""; }
};

export default function MyConsults() {
  const navigate = useNavigate();
  const [items, setItems] = useState(null);

  const load = async () => {
    try { const { data } = await api.get("/consults"); setItems(data); }
    catch { toast.error("Couldn't load your sessions"); setItems([]); }
  };
  useEffect(() => { load(); }, []);

  const cancel = async (id) => {
    try { await api.post(`/consults/${id}/cancel`); toast.success("Cancelled"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Couldn't cancel"); }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-20 h-16 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" className="rounded-full" onClick={() => navigate("/chat")} data-testid="consults-back-button">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <span className="font-display font-semibold text-xl tracking-tight">My sessions</span>
        </div>
        <AccountMenu />
      </header>

      <div className="max-w-2xl mx-auto px-6 py-10">
        {items === null ? (
          <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
        ) : items.length === 0 ? (
          <div className="rounded-2xl border border-border bg-card/30 p-8 text-center" data-testid="consults-empty">
            <Stethoscope className="h-6 w-6 text-muted-foreground mx-auto mb-4" strokeWidth={1.5} />
            <p className="font-medium mb-1">No sessions yet</p>
            <p className="text-sm text-muted-foreground mb-6">When you're ready, there are real people here.</p>
            <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200"
              onClick={() => navigate("/doctors")} data-testid="find-doctor-button">Find a doctor</Button>
          </div>
        ) : (
          <div className="space-y-px bg-border border border-border rounded-2xl overflow-hidden" data-testid="consults-list">
            {items.map((s) => {
              const Icon = MODE_ICON[s.mode] || Video;
              const canJoin = JOINABLE.includes(s.status);
              return (
                <motion.div key={s.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  className="bg-card/60 p-5 flex items-center gap-4" data-testid={`consult-${s.id}`}>
                  <Icon className="h-4 w-4 text-muted-foreground shrink-0" strokeWidth={1.5} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{s.doctor_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {STATUS_LABEL[s.status] || s.status}
                      {s.scheduled_at ? ` · ${fmt(s.scheduled_at)}` : ""}
                      {s.price > 0 ? ` · $${s.price}` : " · Free"}
                    </p>
                  </div>
                  {canJoin && (
                    <Button className="rounded-full bg-primary text-primary-foreground hover:bg-zinc-200 shrink-0"
                      onClick={() => navigate(`/consult/${s.id}`)} data-testid={`join-${s.id}`}>Join</Button>
                  )}
                  {canJoin && (
                    <Button variant="ghost" className="rounded-full text-muted-foreground shrink-0"
                      onClick={() => cancel(s.id)} data-testid={`cancel-${s.id}`}>Cancel</Button>
                  )}
                  {s.status === "completed" && !s.rated && (
                    <Button variant="outline" className="rounded-full border-border shrink-0"
                      onClick={() => navigate(`/consult/${s.id}`)} data-testid={`rate-${s.id}`}>Rate</Button>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
