import React, { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";
import { Loader2, CheckCircle2, KeyRound } from "lucide-react";

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

export default function ResetPassword() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 8) return toast.error("Use at least 8 characters");
    if (password !== confirm) return toast.error("Passwords don't match");
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setDone(true);
      toast.success("Password reset — you can sign in now");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Couldn't reset your password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }} className="w-full max-w-sm">
        <Link to="/" className="font-display font-semibold text-2xl tracking-tight block mb-10">
          Campion<span className="italic font-light">AI</span>
        </Link>

        {!token ? (
          <div data-testid="reset-invalid">
            <h1 className="font-display font-light text-3xl tracking-tight mb-3">Link looks incomplete</h1>
            <p className="text-sm text-muted-foreground mb-8">This reset link is missing its token. Request a new one from the sign-in page.</p>
            <Button onClick={() => navigate("/auth")} className="rounded-full h-12 px-8 bg-primary text-primary-foreground hover:bg-zinc-200">
              Back to sign in
            </Button>
          </div>
        ) : done ? (
          <div data-testid="reset-success">
            <CheckCircle2 className="h-8 w-8 text-emerald-400 mb-5" strokeWidth={1.5} />
            <h1 className="font-display font-light text-3xl tracking-tight mb-3">You're all set</h1>
            <p className="text-sm text-muted-foreground mb-8">Your password has been updated. Sign in with your new password.</p>
            <Button onClick={() => navigate("/auth")} data-testid="reset-goto-login"
              className="rounded-full h-12 px-8 bg-primary text-primary-foreground hover:bg-zinc-200">
              Sign in
            </Button>
          </div>
        ) : (
          <>
            <div className="h-11 w-11 rounded-2xl border border-border bg-white/[0.04] flex items-center justify-center mb-6">
              <KeyRound className="h-5 w-5 text-foreground/80" strokeWidth={1.5} />
            </div>
            <h1 className="font-display font-light text-3xl tracking-tight mb-2">Choose a new password</h1>
            <p className="text-sm text-muted-foreground mb-10">Make it something you'll remember. At least 8 characters.</p>
            <form onSubmit={submit} className="space-y-6">
              <Flushed label="New password" testid="reset-password-input" type="password" required minLength={8}
                placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
              <Flushed label="Confirm password" testid="reset-confirm-input" type="password" required minLength={8}
                placeholder="••••••••" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
              <Button data-testid="reset-submit-button" type="submit" disabled={loading}
                className="w-full rounded-full h-12 text-base bg-primary text-primary-foreground hover:bg-zinc-200 mt-2">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Reset password"}
              </Button>
            </form>
          </>
        )}
      </motion.div>
    </div>
  );
}
