"use client";

/**
 * AdminCharts — lazy-loaded Recharts components for the Admin Dashboard.
 * Dynamically imported with ssr:false to remove Recharts from the shared bundle.
 */
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";

const COLORS = [
  "#8b5cf6",
  "#6366f1",
  "#4f46e5",
  "#3b82f6",
  "#10b981",
  "#059669",
];

interface FunnelChartProps {
  data: { stage: string; count: number }[];
}

export function FunnelChart({ data }: FunnelChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis dataKey="stage" stroke="#9ca3af" fontSize={10} />
        <YAxis stroke="#9ca3af" fontSize={10} />
        <Tooltip
          contentStyle={{ backgroundColor: "#0f1019", border: "1px solid #374151" }}
          labelStyle={{ color: "#fff", fontSize: 11 }}
          itemStyle={{ color: "#a78bfa", fontSize: 11 }}
        />
        <Bar dataKey="count" radius={[8, 8, 0, 0]}>
          {data.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
