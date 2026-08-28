import React from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

const COL = [
  {
    title: "Product",
    links: [
      { label: "Start talking", to: "/auth" },
      { label: "How it works", to: "/#how" },
      { label: "CampionAI Plus", to: "/auth" },
      { label: "Sign in", to: "/auth" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", to: "/about" },
      { label: "Contact", to: "/contact" },
      { label: "FAQ", to: "/faq" },
    ],
  },
  {
    title: "Safety",
    links: [
      { label: "Safety & crisis", to: "/safety" },
      { label: "Privacy", to: "/privacy" },
      { label: "Terms", to: "/terms" },
    ],
  },
];

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="relative z-10 border-t border-border bg-background" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-16 md:py-20">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 md:gap-10">
          {/* Brand */}
          <div className="md:col-span-5">
            <Link to="/" className="inline-flex items-center gap-3" data-testid="footer-brand">
              <span className="font-display font-semibold text-2xl tracking-tight">
                Campion<span className="italic font-light">AI</span>
              </span>
            </Link>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs mt-6">
              A warm, private AI companion that remembers you — and connects you to real people when it matters.
            </p>
            <div className="flex items-center gap-2 mt-8 text-[10px] tracking-[0.25em] uppercase text-muted-foreground">
              <span className="border border-border px-2.5 py-1">AI Companion</span>
              <span className="border border-border px-2.5 py-1">Adults 18+</span>
            </div>
          </div>

          {/* Link columns */}
          <div className="md:col-span-7 grid grid-cols-2 sm:grid-cols-3 gap-8">
            {COL.map((col) => (
              <div key={col.title}>
                <p className="text-[10px] tracking-[0.25em] uppercase text-muted-foreground mb-5">{col.title}</p>
                <ul className="space-y-3">
                  {col.links.map((l) => (
                    <li key={l.label}>
                      <Link
                        to={l.to}
                        className="text-sm text-foreground/80 hover:text-foreground transition-colors inline-flex items-center gap-1 group"
                        data-testid={`footer-link-${l.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                      >
                        {l.label}
                        <ArrowUpRight className="h-3 w-3 opacity-0 -translate-x-1 group-hover:opacity-60 group-hover:translate-x-0 transition-all" />
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-16 pt-8 border-t border-border flex flex-col md:flex-row md:items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground">© {year} CampionAI. All rights reserved.</p>
          <p className="text-xs text-muted-foreground max-w-lg md:text-right leading-relaxed">
            CampionAI is an AI companion — clearly labeled as AI — not a therapist or crisis service.
            If you are in immediate danger, call your local emergency number.
          </p>
        </div>
      </div>
    </footer>
  );
}
