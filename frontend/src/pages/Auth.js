import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";
import { Loader2, MailCheck } from "lucide-react";

const BG_IMG =
  "https://images.pexels.com/photos/36969840/pexels-photo-36969840.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

const Flushed = ({ label, testid, ...props }) => (
  <div>
    <label className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">{label}</label>
    <Input
      data-testid={testid}
      className="mt-1 h-11 rounded-none border-0 border-b border-border bg-transparent px-0 focus-visible:ring-0 focus-visible:border-foreground transition-colors text-base"
      {...props}
    />
  </div>
);

export default function Auth() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState(null);

  const forgot = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      setSent(true);
      setDevLink(data.dev_reset_link || null);
    } catch {
      toast.error("Something went wrong — please try again");
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (m) => {
    setMode(m);
    setSent(false);
    setDevLink(null);
    setPassword("");
  };

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "login") {
        const u = await login(email, password);
        navigate(u.is_admin ? "/admin" : u.onboarded ? "/chat" : "/onboarding");
      } else {
        await register(email, password, name);
        toast.success("Welcome to CampionAI");
        navigate("/onboarding");
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const googleSignIn = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/chat";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      <div className="hidden md:flex md:w-1/2 relative p-14 flex-col justify-between overflow-hidden">
        <img src={BG_IMG} alt="" className="absolute inset-0 w-full h-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-tr from-background via-background/70 to-transparent" />
        <Link to="/" className="relative z-10 font-display font-semibold text-2xl tracking-tight" data-testid="auth-brand-link">
          Campion<span className="italic font-light">AI</span>
        </Link>
        <div className="relative z-10 max-w-sm">
          <h2 className="font-display font-light text-4xl leading-tight tracking-tight mb-5">
            The friend who remembers, listens, and shows up.
          </h2>
          <p className="text-muted-foreground leading-relaxed">Private by design. Warm by nature. A real safety net when it matters.</p>
        </div>
        <p className="relative z-10 text-[10px] tracking-[0.2em] uppercase text-muted-foreground">Adults 18+ · Free for individuals</p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-sm"
        >
          <h1 className="font-display font-light text-4xl tracking-tight mb-2">
            {mode === "login" ? "Welcome back" : mode === "forgot" ? "Reset your password" : "Create your account"}
          </h1>
          <p className="text-sm text-muted-foreground mb-10">
            {mode === "login" ? "Sign in to continue with CampionAI"
              : mode === "forgot" ? "Enter your email and we'll send you a reset link"
              : "It takes less than two minutes"}
          </p>

          {mode === "forgot" ? (
            sent ? (
              <div data-testid="forgot-sent">
                <MailCheck className="h-8 w-8 text-emerald-400 mb-5" strokeWidth={1.5} />
                <p className="text-foreground mb-2">Check your inbox</p>
                <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
                  If <span className="text-foreground">{email}</span> is registered, a reset link is on its way. It expires in 30 minutes.
                </p>
                {devLink && (
                  <div className="mb-8 rounded-2xl border border-amber-400/40 bg-amber-400/[0.06] p-4" data-testid="forgot-dev-link">
                    <p className="text-[10px] tracking-[0.2em] uppercase text-amber-400/90 mb-2">Dev mode · email not configured</p>
                    <p className="text-xs text-muted-foreground mb-3">Email delivery starts once a Resend key is added. Until then, use this link to reset now:</p>
                    <a href={devLink} className="text-sm text-foreground underline underline-offset-2 break-all">{devLink}</a>
                  </div>
                )}
                <button className="text-sm text-foreground font-medium hover:underline underline-offset-4" onClick={() => switchMode("login")} data-testid="forgot-back-to-login">
                  Back to sign in
                </button>
              </div>
            ) : (
              <form onSubmit={forgot} className="space-y-6" data-testid="forgot-form">
                <Flushed label="Email" testid="forgot-email-input" type="email" required placeholder="you@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                <Button data-testid="forgot-submit-button" type="submit" disabled={loading} className="w-full rounded-full h-12 text-base bg-primary text-primary-foreground hover:bg-zinc-200 mt-2">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send reset link"}
                </Button>
                <p className="text-sm text-muted-foreground text-center">
                  Remembered it?{" "}
                  <button type="button" className="text-foreground font-medium hover:underline underline-offset-4" onClick={() => switchMode("login")} data-testid="forgot-cancel">
                    Back to sign in
                  </button>
                </p>
              </form>
            )
          ) : (
          <>
          <form onSubmit={submit} className="space-y-6">
            {mode === "register" && (
              <Flushed label="Preferred name" testid="auth-name-input" placeholder="What should I call you?" value={name} onChange={(e) => setName(e.target.value)} />
            )}
            <Flushed label="Email" testid="auth-email-input" type="email" required placeholder="you@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            <div>
              <Flushed label="Password" testid="auth-password-input" type="password" required minLength={mode === "register" ? 8 : 6} placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
              {mode === "login" && (
                <button type="button" onClick={() => switchMode("forgot")} data-testid="forgot-password-link"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors mt-2">
                  Forgot password?
                </button>
              )}
            </div>
            <Button data-testid="auth-submit-button" type="submit" disabled={loading} className="w-full rounded-full h-12 text-base bg-primary text-primary-foreground hover:bg-zinc-200 mt-2">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <div className="flex items-center gap-4 my-6">
            <div className="h-px flex-1 bg-border" />
            <span className="text-[10px] tracking-[0.25em] uppercase text-muted-foreground">or</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          <button
            type="button"
            data-testid="auth-google-button"
            onClick={googleSignIn}
            className="w-full h-12 rounded-full border border-border bg-transparent hover:bg-muted/40 transition-colors flex items-center justify-center gap-3 text-sm font-medium"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.98.66-2.24 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.11a6.6 6.6 0 0 1 0-4.22V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84z" />
              <path fill="#EA4335" d="M12 4.75c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 1.4 14.97.4 12 .4A11 11 0 0 0 2.18 7.05l3.66 2.84C6.71 6.68 9.14 4.75 12 4.75z" />
            </svg>
            Continue with Google
          </button>

          <p className="text-sm text-muted-foreground mt-8 text-center">
            {mode === "login" ? "New here? " : "Already have an account? "}
            <button data-testid="auth-toggle-mode" className="text-foreground font-medium hover:underline underline-offset-4" onClick={() => switchMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
          </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
