import React, { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
// Handles the Emergent Google OAuth return: reads session_id from the URL fragment,
// exchanges it server-side for an app JWT, then routes the user into the app.
export default function AuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : null;

    (async () => {
      if (!sessionId) {
        navigate("/auth", { replace: true });
        return;
      }
      try {
        const { data } = await api.post("/auth/google/session", { session_id: sessionId });
        localStorage.setItem("campion_token", data.token);
        setUser(data.user);
        // Clear the session_id fragment from the URL.
        window.history.replaceState(null, "", window.location.pathname);
        if (data.user.is_admin) navigate("/admin", { replace: true });
        else if (!data.user.onboarded) navigate("/onboarding", { replace: true });
        else navigate("/chat", { replace: true });
      } catch (e) {
        navigate("/auth?error=google", { replace: true });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-4">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
      <p className="text-sm text-muted-foreground tracking-wide">Signing you in…</p>
    </div>
  );
}
