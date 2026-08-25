import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";
import { Loader2 } from "lucide-react";

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
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h1>
          <p className="text-sm text-muted-foreground mb-10">
            {mode === "login" ? "Sign in to continue with CampionAI" : "It takes less than two minutes"}
          </p>

          <form onSubmit={submit} className="space-y-6">
            {mode === "register" && (
              <Flushed label="Preferred name" testid="auth-name-input" placeholder="What should I call you?" value={name} onChange={(e) => setName(e.target.value)} />
            )}
            <Flushed label="Email" testid="auth-email-input" type="email" required placeholder="you@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Flushed label="Password" testid="auth-password-input" type="password" required minLength={6} placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
            <Button data-testid="auth-submit-button" type="submit" disabled={loading} className="w-full rounded-full h-12 text-base bg-primary text-primary-foreground hover:bg-zinc-200 mt-2">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground mt-8 text-center">
            {mode === "login" ? "New here? " : "Already have an account? "}
            <button data-testid="auth-toggle-mode" className="text-foreground font-medium hover:underline underline-offset-4" onClick={() => setMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
