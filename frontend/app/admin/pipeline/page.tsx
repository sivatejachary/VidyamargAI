"use client";

import ReactFlow, { Background, Controls, MarkerType } from "reactflow";
import "reactflow/dist/style.css";
import { GitFork } from "lucide-react";

export default function AdminPipeline() {
  const nodes = [
    {
      id: "1",
      data: { label: "Resume Collection Agent" },
      position: { x: 50, y: 200 },
      style: { background: "#1e1b4b", color: "#a5b4fc", border: "1px solid #4f46e5", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "2",
      data: { label: "Resume Parsing Agent" },
      position: { x: 250, y: 200 },
      style: { background: "#1e1b4b", color: "#a5b4fc", border: "1px solid #4f46e5", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "3",
      data: { label: "Resume Screening Agent" },
      position: { x: 450, y: 200 },
      style: { background: "#1e1b4b", color: "#a5b4fc", border: "1px solid #4f46e5", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "4",
      data: { label: "Assessment Gen Agent" },
      position: { x: 650, y: 200 },
      style: { background: "#3b0764", color: "#f3e8ff", border: "1px solid #9333ea", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "5",
      data: { label: "AI Proctoring Agent" },
      position: { x: 850, y: 100 },
      style: { background: "#450a0a", color: "#fee2e2", border: "1px solid #dc2626", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "6",
      data: { label: "Assessment Eval Agent" },
      position: { x: 850, y: 300 },
      style: { background: "#3b0764", color: "#f3e8ff", border: "1px solid #9333ea", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "7",
      data: { label: "Tara Interview Agent" },
      position: { x: 1050, y: 200 },
      style: { background: "#172554", color: "#dbeafe", border: "1px solid #2563eb", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "8",
      data: { label: "Interview Analysis Agent" },
      position: { x: 1250, y: 200 },
      style: { background: "#172554", color: "#dbeafe", border: "1px solid #2563eb", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "9",
      data: { label: "Candidate Ranking Agent" },
      position: { x: 1450, y: 200 },
      style: { background: "#1e1b4b", color: "#a5b4fc", border: "1px solid #4f46e5", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "10",
      data: { label: "Hiring Rec Agent" },
      position: { x: 1650, y: 200 },
      style: { background: "#1e1b4b", color: "#a5b4fc", border: "1px solid #4f46e5", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "11",
      data: { label: "Offer Gen Agent" },
      position: { x: 1850, y: 200 },
      style: { background: "#064e3b", color: "#d1fae5", border: "1px solid #059669", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    },
    {
      id: "12",
      data: { label: "Onboarding Agent" },
      position: { x: 2050, y: 200 },
      style: { background: "#064e3b", color: "#d1fae5", border: "1px solid #059669", borderRadius: "10px", padding: "10px", fontSize: "11px", fontWeight: "bold", width: 160 }
    }
  ];

  const edges = [
    { id: "e1-2", source: "1", target: "2", markerEnd: { type: MarkerType.ArrowClosed, color: "#4f46e5" }, style: { stroke: "#4f46e5" } },
    { id: "e2-3", source: "2", target: "3", markerEnd: { type: MarkerType.ArrowClosed, color: "#4f46e5" }, style: { stroke: "#4f46e5" } },
    { id: "e3-4", source: "3", target: "4", markerEnd: { type: MarkerType.ArrowClosed, color: "#4f46e5" }, style: { stroke: "#4f46e5" } },
    // Branching off to proctor and evaluation
    { id: "e4-5", source: "4", target: "5", markerEnd: { type: MarkerType.ArrowClosed, color: "#dc2626" }, style: { stroke: "#9333ea" } },
    { id: "e4-6", source: "4", target: "6", markerEnd: { type: MarkerType.ArrowClosed, color: "#9333ea" }, style: { stroke: "#9333ea" } },
    { id: "e5-6", source: "5", target: "6", markerEnd: { type: MarkerType.ArrowClosed, color: "#dc2626" }, style: { stroke: "#dc2626", strokeDasharray: "5 5" } },
    // Back to sequence
    { id: "e6-7", source: "6", target: "7", markerEnd: { type: MarkerType.ArrowClosed, color: "#2563eb" }, style: { stroke: "#2563eb" } },
    { id: "e7-8", source: "7", target: "8", markerEnd: { type: MarkerType.ArrowClosed, color: "#2563eb" }, style: { stroke: "#2563eb" } },
    { id: "e8-9", source: "8", target: "9", markerEnd: { type: MarkerType.ArrowClosed, color: "#4f46e5" }, style: { stroke: "#4f46e5" } },
    { id: "e9-10", source: "9", target: "10", markerEnd: { type: MarkerType.ArrowClosed, color: "#4f46e5" }, style: { stroke: "#4f46e5" } },
    { id: "e10-11", source: "10", target: "11", markerEnd: { type: MarkerType.ArrowClosed, color: "#059669" }, style: { stroke: "#059669" } },
    { id: "e11-12", source: "11", target: "12", markerEnd: { type: MarkerType.ArrowClosed, color: "#059669" }, style: { stroke: "#059669" } }
  ];

  return (
    <div className="p-8 md:p-12 max-w-7xl mx-auto flex flex-col gap-8 h-[88vh]">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <span>AI Recruiting Workflow Engine</span>
          <GitFork size={20} className="text-purple-400" />
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Visual layout of the 12 autonomous agent pipelines coordinating Candidate profiles through validation loops.
        </p>
      </div>

      {/* React Flow Box */}
      <div className="flex-1 glass-panel rounded-2xl border border-gray-800 bg-background/60 overflow-hidden relative">
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background color="#1f2937" gap={16} size={1} />
          <Controls className="bg-purple-900 border-purple-500 text-white rounded" />
        </ReactFlow>
      </div>
    </div>
  );
}
