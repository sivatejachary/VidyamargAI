"use client";

import { LearningRoadmap } from "@/types/lms.types";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ProgressBar } from "@/components/ui/Progress";

interface RoadmapCardProps {
  roadmap: LearningRoadmap;
  currentStep?: number;
  progress?: number;
  onStart?: (roadmap: LearningRoadmap) => void;
}

export default function RoadmapCard({
  roadmap,
  currentStep,
  progress = 0,
  onStart,
}: RoadmapCardProps) {
  const isEnrolled = currentStep !== undefined && currentStep >= 0;

  return (
    <Card hoverEffect className="p-5 h-full flex flex-col gap-3">
      {/* Header */}
      <div>
        <h3 className="text-base font-bold text-foreground">{roadmap.name}</h3>
        <p className="text-xs text-muted-foreground">
          {roadmap.totalCourses} courses · {roadmap.totalHours}h
        </p>
      </div>

      {/* Step sequence */}
      <div
        className="flex flex-wrap gap-1.5 items-center"
        role="list"
        aria-label={`Steps for ${roadmap.name}`}
      >
        {roadmap.steps.map((step, index) => {
          const isCompleteOrCurrent = isEnrolled && index <= currentStep!;
          const isCurrent = isEnrolled && index === currentStep;

          return (
            <div key={index} className="flex items-center gap-1.5" role="listitem">
              {index > 0 && (
                <span className="text-xs text-muted-foreground" aria-hidden="true">
                  →
                </span>
              )}
              <span
                className={[
                  "px-2.5 py-1 rounded-lg text-xs font-medium transition-colors",
                  isCompleteOrCurrent
                    ? "bg-primary/15 text-primary border border-primary/30"
                    : "bg-muted text-muted-foreground",
                  isCurrent ? "ring-2 ring-primary/40" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {step}
              </span>
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      {progress > 0 && (
        <div className="flex flex-col gap-1">
          <ProgressBar value={progress} />
          <span className="text-xs text-muted-foreground">
            {progress}% complete
          </span>
        </div>
      )}

      {/* CTA */}
      <div className="mt-auto">
        <Button
          variant={progress > 0 ? "outline" : "primary"}
          size="xs"
          className="w-full"
          aria-label={
            progress > 0
              ? `Continue path: ${roadmap.name}`
              : `Start path: ${roadmap.name}`
          }
          onClick={() => onStart?.(roadmap)}
        >
          {progress > 0 ? "Continue Path" : "Start Path"}
        </Button>
      </div>
    </Card>
  );
}
