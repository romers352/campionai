import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import Footer from "@/components/Footer";

/**
 * Shared shell for public content pages (Privacy, Terms, About, etc.).
 * Provides the sticky glass nav, an editorial hero header, a content
 * container, and the site footer — all on the Obsidian & Platinum theme.
 */
export default function PageShell({ eyebrow, title, subtitle, children, testId }) {
  useEffect(() => { window.scrollTo(0, 0); }, []);

  return (
    <div className="min-h-screen bg-background text-foreground relative flex flex-col" data-testid={testId}>
      {/* Nav */}
      <nav className="sticky top-0 z-30 glass">
        <div className="max-w-7xl mx-auto px-6 md:px-10 h-20 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3" data-testid="page-brand-logo">
            <span className="font-display font-semibold text-2xl tracking-tight">
              Campion<span className="italic font-light">AI</span>
            </span>
          </Link>
          <div className="flex items-center gap-2">
            <Link to="/auth" data-testid="page-signin-link">
              <Button variant="ghost" className="rounded-full text-muted-foreground hover:text-foreground">Sign in</Button>
            </Link>
            <Link to="/auth" data-testid="page-getstarted-link">
              <Button className="rounded-full px-6 bg-primary text-primary-foreground hover:bg-zinc-200">Get started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero header */}
      <header className="relative overflow-hidden border-b border-border">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 h-96 w-[42rem] rounded-full bg-white/[0.04] blur-[120px]" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-6 md:px-10 pt-16 pb-14 md:pt-24 md:pb-20">
          <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-10" data-testid="page-back-home">
            <ArrowLeft className="h-4 w-4" /> Back home
          </Link>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          >
            {eyebrow && (
              <p className="text-[10px] tracking-[0.3em] uppercase text-muted-foreground mb-6">{eyebrow}</p>
            )}
            <h1 className="font-display font-light text-4xl md:text-6xl tracking-tight leading-[1.02] mb-5">{title}</h1>
            {subtitle && <p className="text-lg text-muted-foreground max-w-2xl leading-relaxed">{subtitle}</p>}
          </motion.div>
        </div>
      </header>

      {/* Content */}
      <main className="relative z-10 flex-1 max-w-4xl mx-auto w-full px-6 md:px-10 py-16 md:py-20">
        {children}
      </main>

      <Footer />
    </div>
  );
}

/* Reusable prose helpers for content pages */
export function Section({ title, children }) {
  return (
    <section className="border-t border-border pt-10 mt-10 first:border-t-0 first:pt-0 first:mt-0">
      {title && <h2 className="font-display font-medium text-2xl md:text-3xl tracking-tight mb-5">{title}</h2>}
      <div className="space-y-4 text-[15px] leading-relaxed text-muted-foreground max-w-2xl">{children}</div>
    </section>
  );
}
