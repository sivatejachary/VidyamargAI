"use client";

import { SKILL_CHIPS } from "@/types/lms.types";

interface SkillFilterChipsProps {
  chips: readonly string[];
  activeChip: string;
  onSelect: (chip: string) => void;
}

export default function SkillFilterChips({
  chips,
  activeChip,
  onSelect,
}: SkillFilterChipsProps) {
  return (
    <div className="overflow-x-auto scrollbar-hide">
      <div className="flex flex-nowrap gap-2">
        {chips.map((chip) => {
          const isActive = chip === activeChip;

          return (
            <button
              key={chip}
              type="button"
              onClick={() => onSelect(chip)}
              aria-label={`Filter by ${chip}`}
              aria-pressed={isActive}
              className={`
                flex-shrink-0 px-3.5 py-2 rounded-xl text-xs font-semibold cursor-pointer
                transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-ring
                ${
                  isActive
                    ? "bg-primary text-primary-foreground font-bold"
                    : "bg-card border border-border text-muted-foreground hover:border-primary/40 hover:text-foreground"
                }
              `}
            >
              {chip}
            </button>
          );
        })}
      </div>
    </div>
  );
}
