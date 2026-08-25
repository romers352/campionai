import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/sonner";
import { HeartHandshake, Loader2 } from "lucide-react";

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
      <div className="hidden md:flex md:w-1/2 bg-primary text-primary-foreground p-14 flex-col justify-between relative">
        <Link to="/" className="flex items-center gap-2.5" data-testid="auth-brand-link">
          <div className="h-8 w-8 rounded-xl bg-primary-foreground/20 flex items-center justify-center">
            <HeartHandshake className="h-4 w-4" />
          </div>
          <span className="font-display font-extrabold text-lg">CampionAI</span>
        </Link>
        <div className="max-w-sm">
          <h2 className="text-3xl font-extrabold font-display tracking-tight leading-tight mb-4">
            The friend who remembers, listens, and shows up.
          </h2>
          <p className="text-primary-foreground/80 leading-relaxed">
            Private by design. Warm by nature. A real safety net when it matters.
          </p>
        </div>
        <p className="text-xs text-primary-foreground/60">Adults 18+ · Free for individuals</p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-sm"
        >
          <h1 className="text-3xl font-extrabold font-display tracking-tight mb-1">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h1>
          <p className="text-sm text-muted-foreground mb-8">
            {mode === "login" ? "Sign in to continue with CampionAI" : "It takes less than two minutes"}
          </p>

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div>
                <Label className="text-sm">Preferred name</Label>
                <Input
                  data-testid="auth-name-input"
                  className="mt-1.5 rounded-full h-11"
                  placeholder="What should I call you?"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            )}
            <div>
              <Label className="text-sm">Email</Label>
              <Input
                data-testid="auth-email-input"
                type="email"
                required
                className="mt-1.5 rounded-full h-11"
                placeholder="you@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <Label className="text-sm">Password</Label>
              <Input
                data-testid="auth-password-input"
                type="password"
                required
                minLength={6}
                className="mt-1.5 rounded-full h-11"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <Button data-testid="auth-submit-button" type="submit" disabled={loading} className="w-full rounded-full h-11 text-base">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <p className="text-sm text-muted-foreground mt-6 text-center">
            {mode === "login" ? "New here? " : "Already have an account? "}
            <button
              data-testid="auth-toggle-mode"
              className="text-primary font-medium hover:underline"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
