"use client";

import React, { useState } from "react";
import { Check, Loader2, Calendar, Clock, Upload, ArrowRight, UserCheck, ShieldAlert } from "lucide-react";

export interface InteractiveCardProps {
  card: {
    type: string;
    title: string;
    description?: string;
    required?: boolean;
    field: string;
    options?: { id: string; label: string }[];
    min?: number;
    max?: number;
    step?: number;
    default?: any;
    steps?: { label: string; status: string }[];
  };
  onSubmit: (field: string, value: any) => void;
  disabled?: boolean;
}

export default function AIInteractiveCard({ card, onSubmit, disabled = false }: InteractiveCardProps) {
  const [selectedValue, setSelectedValue] = useState<any>(card.default || "");
  const [selectedList, setSelectedList] = useState<string[]>(card.default || []);
  const [textVal, setTextVal] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled || isSubmitting) return;
    setIsSubmitting(true);
    
    let finalVal = selectedValue;
    if (card.type === "multi_select") {
      finalVal = selectedList;
    } else if (card.type === "text" || card.type === "textarea") {
      finalVal = textVal;
    }
    
    onSubmit(card.field, finalVal);
  };

  const renderComponent = () => {
    switch (card.type) {
      case "single_select":
        return (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
            {card.options?.map((opt) => (
              <button
                key={opt.id}
                type="button"
                disabled={disabled}
                onClick={() => {
                  setSelectedValue(opt.id);
                  onSubmit(card.field, opt.id);
                }}
                className={`
                  p-3.5 rounded-xl border text-xs font-semibold text-left transition-all duration-200
                  ${selectedValue === opt.id 
                    ? "border-primary bg-primary/10 text-primary shadow-sm" 
                    : "border-border bg-card text-muted-foreground hover:bg-muted/30 hover:text-foreground"
                  }
                `}
              >
                {opt.label}
              </button>
            ))}
          </div>
        );

      case "multi_select":
        return (
          <div className="space-y-2 mt-3">
            {card.options?.map((opt) => {
              const isChecked = selectedList.includes(opt.id);
              return (
                <button
                  key={opt.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    const next = isChecked 
                      ? selectedList.filter(x => x !== opt.id) 
                      : [...selectedList, opt.id];
                    setSelectedList(next);
                  }}
                  className={`
                    w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold transition-all
                    ${isChecked 
                      ? "border-primary bg-primary/5 text-foreground" 
                      : "border-border bg-card text-muted-foreground hover:bg-muted/30 hover:text-foreground"
                    }
                  `}
                >
                  <span>{opt.label}</span>
                  <div className={`
                    w-4 h-4 rounded border flex items-center justify-center transition-colors
                    ${isChecked ? "bg-primary border-primary" : "border-muted-foreground/35"}
                  `}>
                    {isChecked && <Check size={10} className="text-white" />}
                  </div>
                </button>
              );
            })}
            <button
              type="button"
              disabled={disabled || selectedList.length === 0}
              onClick={handleSubmit}
              className="w-full mt-3 p-3 rounded-xl bg-primary text-white text-xs font-bold hover:opacity-95 transition-opacity"
            >
              Continue
            </button>
          </div>
        );

      case "chips":
        return (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {card.options?.map((opt) => (
              <button
                key={opt.id}
                type="button"
                disabled={disabled}
                onClick={() => onSubmit(card.field, opt.id)}
                className="px-3 py-1.5 rounded-full border border-border bg-card hover:bg-muted/30 text-[11px] font-semibold text-muted-foreground hover:text-foreground transition-all"
              >
                {opt.label}
              </button>
            ))}
          </div>
        );

      case "slider":
        return (
          <div className="mt-3 space-y-3">
            <input
              type="range"
              min={card.min || 0}
              max={card.max || 100}
              step={card.step || 1}
              value={selectedValue || card.min || 0}
              disabled={disabled}
              onChange={(e) => setSelectedValue(Number(e.target.value))}
              className="w-full h-1.5 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
            <div className="flex justify-between items-center text-xs font-bold text-muted-foreground">
              <span>{card.min || 0}</span>
              <span className="text-primary text-sm">{selectedValue || card.min || 0}</span>
              <span>{card.max || 100}</span>
            </div>
            <button
              type="button"
              disabled={disabled}
              onClick={handleSubmit}
              className="w-full p-3 rounded-xl bg-primary text-white text-xs font-bold hover:opacity-95 transition-opacity"
            >
              Submit Value
            </button>
          </div>
        );

      case "upload":
      case "image_upload":
        return (
          <div className="mt-3">
            <label className="flex flex-col items-center justify-center border-2 border-dashed border-border rounded-2xl p-6 bg-card hover:bg-muted/30 cursor-pointer transition-all duration-300">
              <Upload className="text-muted-foreground/60 mb-2 animate-bounce" size={24} />
              <span className="text-xs font-bold text-foreground">Upload Files</span>
              <span className="text-[10px] text-muted-foreground mt-0.5">Supported: PDF, DOCX, Images</span>
              <input
                type="file"
                disabled={disabled}
                onChange={() => onSubmit(card.field, "uploaded_file_placeholder.pdf")}
                className="hidden"
              />
            </label>
          </div>
        );

      case "timeline":
      case "progress":
        return (
          <div className="space-y-3 mt-3">
            {card.steps?.map((step, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className={`
                  w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0
                  ${step.status === "completed" 
                    ? "bg-emerald-500 text-white" 
                    : step.status === "running" 
                      ? "bg-primary text-white animate-spin" 
                      : "bg-muted text-muted-foreground"
                  }
                `}>
                  {step.status === "completed" ? "✓" : step.status === "running" ? "⟳" : idx + 1}
                </div>
                <span className="text-xs font-semibold text-foreground">{step.label}</span>
              </div>
            ))}
          </div>
        );

      case "approval":
        return (
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSubmit(card.field, "approve")}
              className="flex-1 p-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors"
            >
              Approve Action
            </button>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSubmit(card.field, "reject")}
              className="flex-1 p-3 rounded-xl bg-destructive hover:bg-destructive/90 text-white text-xs font-bold transition-colors"
            >
              Reject
            </button>
          </div>
        );

      default:
        return (
          <form onSubmit={handleSubmit} className="mt-3 space-y-2">
            {card.type === "textarea" ? (
              <textarea
                required={card.required}
                disabled={disabled}
                placeholder="Type your response..."
                value={textVal}
                onChange={(e) => setTextVal(e.target.value)}
                className="w-full p-3 rounded-xl border border-border bg-card text-xs text-foreground focus:outline-none focus:border-primary/50 min-h-24 resize-none"
              />
            ) : (
              <div className="flex gap-2">
                <input
                  type={card.type === "calendar" ? "date" : card.type === "time_picker" ? "time" : "text"}
                  required={card.required}
                  disabled={disabled}
                  placeholder="Enter details..."
                  value={textVal}
                  onChange={(e) => setTextVal(e.target.value)}
                  className="flex-1 p-3 rounded-xl border border-border bg-card text-xs text-foreground focus:outline-none focus:border-primary/50"
                />
                <button
                  type="submit"
                  disabled={disabled}
                  className="p-3 rounded-xl bg-primary text-white hover:opacity-95 transition-opacity"
                >
                  <ArrowRight size={14} />
                </button>
              </div>
            )}
          </form>
        );
    }
  };

  return (
    <div className="relative border border-border bg-card/65 backdrop-blur-md rounded-2xl p-4 shadow-sm overflow-hidden group transition-all duration-300">
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-indigo-500 opacity-60" />
      <h4 className="text-xs font-bold text-foreground flex items-center gap-1.5">
        {card.type === "approval" ? <ShieldAlert size={14} className="text-amber-500" /> : <UserCheck size={14} className="text-blue-500" />}
        {card.title}
      </h4>
      {card.description && (
        <p className="text-[10px] text-muted-foreground mt-0.5 leading-snug">{card.description}</p>
      )}
      {renderComponent()}
    </div>
  );
}
