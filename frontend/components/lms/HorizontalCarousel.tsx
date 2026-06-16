"use client";

import React, { useRef, useState, useCallback, useEffect, memo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { CarouselVariant } from "@/types/lms.types";

/* ═══════════════════════════════════════════════════════
   HorizontalCarousel — Reusable Netflix/Udemy-style
   horizontal scroll carousel.
   ═══════════════════════════════════════════════════════ */

interface HorizontalCarouselProps<T> {
  title: string;
  subtitle?: string;
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  itemWidth?: number;
  showArrows?: boolean;
  variant?: CarouselVariant;
  emptyState?: React.ReactNode;
  onSeeAll?: () => void;
  onScrollProgress?: (progress: number) => void;
}

/** Memoized carousel item wrapper to prevent re-renders on scroll */
const CarouselItem = memo(function CarouselItem({
  children,
  width,
}: {
  children: React.ReactNode;
  width: number;
}) {
  return (
    <div
      className="shrink-0 snap-start"
      style={{ width }}
    >
      {children}
    </div>
  );
});

const VARIANT_CONFIG: Record<CarouselVariant, { desktopWidth: number; tabletWidth: number; mobileWidth: number; gap: number }> = {
  course:  { desktopWidth: 240, tabletWidth: 220, mobileWidth: 200, gap: 16 },
  career:  { desktopWidth: 360, tabletWidth: 320, mobileWidth: 280, gap: 20 },
  roadmap: { desktopWidth: 340, tabletWidth: 300, mobileWidth: 260, gap: 20 },
};

function HorizontalCarouselInner<T>({
  title,
  subtitle,
  items,
  renderItem,
  itemWidth: itemWidthProp,
  showArrows = true,
  variant = "course",
  emptyState,
  onSeeAll,
  onScrollProgress,
}: HorizontalCarouselProps<T>) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [currentWidth, setCurrentWidth] = useState(
    itemWidthProp ?? VARIANT_CONFIG[variant].desktopWidth
  );
  const prefersReducedMotion = usePrefersReducedMotion();

  const gap = VARIANT_CONFIG[variant].gap;

  /* ─── Responsive width via ResizeObserver ─── */
  useEffect(() => {
    if (itemWidthProp) {
      setCurrentWidth(itemWidthProp);
      return;
    }
    const config = VARIANT_CONFIG[variant];
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 0;
      if (w < 640) setCurrentWidth(config.mobileWidth);
      else if (w < 1024) setCurrentWidth(config.tabletWidth);
      else setCurrentWidth(config.desktopWidth);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [itemWidthProp, variant]);

  /* ─── Scroll state tracking ─── */
  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const tolerance = 2;
    setCanScrollLeft(el.scrollLeft > tolerance);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - tolerance);

    if (onScrollProgress && el.scrollWidth > el.clientWidth) {
      const progress = el.scrollLeft / (el.scrollWidth - el.clientWidth);
      onScrollProgress(Math.min(1, Math.max(0, progress)));
    }
  }, [onScrollProgress]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    updateScrollState();
    el.addEventListener("scroll", updateScrollState, { passive: true });
    return () => el.removeEventListener("scroll", updateScrollState);
  }, [updateScrollState, items.length]);

  /* Re-check scroll state when items or width changes */
  useEffect(() => {
    requestAnimationFrame(updateScrollState);
  }, [items.length, currentWidth, updateScrollState]);

  /* ─── Arrow click handler ─── */
  const scroll = useCallback(
    (direction: "left" | "right") => {
      const el = scrollRef.current;
      if (!el) return;
      const scrollAmount = (currentWidth + gap) * 3;
      el.scrollBy({
        left: direction === "left" ? -scrollAmount : scrollAmount,
        behavior: prefersReducedMotion ? "auto" : "smooth",
      });
    },
    [currentWidth, gap, prefersReducedMotion]
  );

  /* ─── Keyboard navigation ─── */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        scroll("left");
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        scroll("right");
      }
    },
    [scroll]
  );

  if (!items.length && !emptyState) return null;

  return (
    <section
      ref={containerRef}
      className="w-full"
      aria-roledescription="carousel"
      aria-label={title}
    >
      {/* ── Section Header ── */}
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-foreground">{title}</h2>
          {subtitle && (
            <p className="text-sm text-muted-foreground mt-0.5">{subtitle}</p>
          )}
        </div>
        {onSeeAll && items.length > 0 && (
          <button
            onClick={onSeeAll}
            className="text-sm font-semibold text-primary hover:text-primary/80 transition-colors cursor-pointer flex items-center gap-1"
            aria-label={`See all ${title}`}
          >
            See All
            <ChevronRight size={14} />
          </button>
        )}
      </div>

      {/* ── Empty state ── */}
      {items.length === 0 && emptyState ? (
        <div className="py-8">{emptyState}</div>
      ) : (
        /* ── Carousel container ── */
        <div
          className="relative group"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          onKeyDown={handleKeyDown}
          tabIndex={0}
          role="group"
          aria-label={`${title} carousel`}
        >
          {/* Gradient fade edges (desktop only) */}
          {canScrollLeft && (
            <div className="hidden lg:block absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-background to-transparent z-10 pointer-events-none" />
          )}
          {canScrollRight && (
            <div className="hidden lg:block absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-background to-transparent z-10 pointer-events-none" />
          )}

          {/* Left Arrow */}
          {showArrows && canScrollLeft && (
            <button
              onClick={() => scroll("left")}
              className={`absolute left-0 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full bg-card border border-border shadow-lg flex items-center justify-center cursor-pointer transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring hover:bg-muted ${
                isHovered ? "opacity-100" : "opacity-0"
              } lg:flex hidden`}
              aria-label="Scroll left"
            >
              <ChevronLeft size={18} className="text-foreground" />
            </button>
          )}

          {/* Right Arrow */}
          {showArrows && canScrollRight && (
            <button
              onClick={() => scroll("right")}
              className={`absolute right-0 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full bg-card border border-border shadow-lg flex items-center justify-center cursor-pointer transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring hover:bg-muted ${
                isHovered ? "opacity-100" : "opacity-0"
              } lg:flex hidden`}
              aria-label="Scroll right"
            >
              <ChevronRight size={18} className="text-foreground" />
            </button>
          )}

          {/* Scrollable track */}
          <div
            ref={scrollRef}
            className="flex overflow-x-auto scrollbar-hide will-change-transform snap-x snap-mandatory"
            style={{ gap }}
          >
            {items.map((item, index) => (
              <CarouselItem key={index} width={currentWidth}>
                {renderItem(item, index)}
              </CarouselItem>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export const HorizontalCarousel = memo(HorizontalCarouselInner) as typeof HorizontalCarouselInner;

/* ─── Utility hook ─── */
function usePrefersReducedMotion(): boolean {
  const [prefersReduced, setPrefersReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return prefersReduced;
}
