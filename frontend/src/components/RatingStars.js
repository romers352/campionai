import React, { useState } from "react";
import { Star } from "lucide-react";

/** Read-only display, or an interactive picker when onChange is supplied. */
export default function RatingStars({ value = 0, count, onChange, size = "h-4 w-4", testid }) {
  const [hover, setHover] = useState(0);
  const interactive = typeof onChange === "function";
  const shown = hover || value;

  return (
    <span className="inline-flex items-center gap-1" data-testid={testid}>
      {[1, 2, 3, 4, 5].map((n) => {
        const filled = n <= Math.round(shown);
        const star = (
          <Star
            className={`${size} ${filled ? "fill-foreground text-foreground" : "text-muted-foreground"}`}
            strokeWidth={1.5}
          />
        );
        return interactive ? (
          <button
            key={n}
            type="button"
            aria-label={`${n} star${n > 1 ? "s" : ""}`}
            data-testid={`${testid || "rating"}-star-${n}`}
            onMouseEnter={() => setHover(n)}
            onMouseLeave={() => setHover(0)}
            onClick={() => onChange(n)}
            className="focus:outline-none focus:ring-2 focus:ring-ring rounded"
          >
            {star}
          </button>
        ) : (
          <span key={n}>{star}</span>
        );
      })}
      {!interactive && typeof count === "number" && (
        <span className="ml-1 text-xs text-muted-foreground">
          {value ? value.toFixed(1) : "New"}{count ? ` (${count})` : ""}
        </span>
      )}
    </span>
  );
}
