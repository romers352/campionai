import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import SettingsDialog from "@/components/SettingsDialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { LogOut, Settings, CreditCard, MessageCircle, Stethoscope, Sparkles, LayoutDashboard, CalendarClock, HeartHandshake } from "lucide-react";

/**
 * Account menu — the only place logout lives. Mounted in every authenticated page
 * header so signing out never depends on which page you happen to be on.
 */
export default function AccountMenu({ align = "end" }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [settingsOpen, setSettingsOpen] = useState(false);

  if (!user) return null;

  const initial = (user.profile?.preferred_name || user.email || "?").trim().charAt(0).toUpperCase();
  const isDoctor = user.role === "doctor";

  const go = (path) => () => navigate(path);

  const signOut = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            data-testid="account-menu-trigger"
            aria-label="Account menu"
            className="h-9 w-9 shrink-0 rounded-full border border-border bg-white/[0.04] text-sm font-medium text-foreground/80 transition-colors hover:bg-accent focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {initial}
          </button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align={align} className="w-56">
          <div className="px-2 py-1.5">
            <p className="truncate text-sm font-medium">{user.profile?.preferred_name || "Account"}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          </div>
          <DropdownMenuSeparator />

          {!user.is_admin && !isDoctor && (
            <>
              <DropdownMenuItem onSelect={go("/chat")} data-testid="menu-chat">
                <MessageCircle className="mr-2 h-4 w-4" strokeWidth={1.5} /> Chat
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={go("/doctors")} data-testid="menu-doctors">
                <Stethoscope className="mr-2 h-4 w-4" strokeWidth={1.5} /> Talk to a doctor
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={go("/consults")} data-testid="menu-consults">
                <CalendarClock className="mr-2 h-4 w-4" strokeWidth={1.5} /> My sessions
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={go("/wellness")} data-testid="menu-wellness">
                <Sparkles className="mr-2 h-4 w-4" strokeWidth={1.5} /> Wellness
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={go("/billing")} data-testid="menu-billing">
                <CreditCard className="mr-2 h-4 w-4" strokeWidth={1.5} /> Billing
              </DropdownMenuItem>
            </>
          )}

          {isDoctor && (
            <DropdownMenuItem onSelect={go("/doctor")} data-testid="menu-doctor-dashboard">
              <LayoutDashboard className="mr-2 h-4 w-4" strokeWidth={1.5} /> Doctor dashboard
            </DropdownMenuItem>
          )}

          {user.is_admin && (
            <DropdownMenuItem onSelect={go("/admin")} data-testid="menu-admin">
              <LayoutDashboard className="mr-2 h-4 w-4" strokeWidth={1.5} /> Admin
            </DropdownMenuItem>
          )}

          {!user.is_admin && !isDoctor && (
            <>
              <DropdownMenuItem onSelect={() => setSettingsOpen(true)} data-testid="menu-settings">
                <Settings className="mr-2 h-4 w-4" strokeWidth={1.5} /> Settings
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={go("/doctor/apply")} data-testid="menu-doctor-apply">
                <HeartHandshake className="mr-2 h-4 w-4" strokeWidth={1.5} /> I'm a doctor
              </DropdownMenuItem>
            </>
          )}

          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={signOut} data-testid="logout-button">
            <LogOut className="mr-2 h-4 w-4" strokeWidth={1.5} /> Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
