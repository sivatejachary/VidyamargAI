"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Send, RefreshCw, AlertCircle, ToggleLeft, ToggleRight, Check } from "lucide-react";
import { apiService } from "@/services/api";

interface TelegramSource {
  id: number;
  channel_name: string;
  active: boolean;
  last_checked: string | null;
}

export default function TelegramSources() {
  const [sources, setSources] = useState<TelegramSource[]>([]);
  const [newChannel, setNewChannel] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getTelegramSources();
      setSources(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch Telegram sources");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSources();
  }, []);

  const handleAddChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newChannel.trim()) return;

    setActionLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const formattedChannel = newChannel.trim().replace(/^@/, "");
      await apiService.createTelegramSource(formattedChannel, true);
      setNewChannel("");
      setSuccess(`Channel @${formattedChannel} added successfully!`);
      fetchSources();
    } catch (err: any) {
      setError(err.message || "Failed to add Telegram source");
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleActive = async (source: TelegramSource) => {
    setError(null);
    setSuccess(null);
    try {
      await apiService.updateTelegramSource(source.id, source.channel_name, !source.active);
      setSources((prev) =>
        prev.map((s) => (s.id === source.id ? { ...s, active: !s.active } : s))
      );
      setSuccess(`Channel @${source.channel_name} ${!source.active ? "enabled" : "disabled"} successfully!`);
    } catch (err: any) {
      setError(err.message || "Failed to update Telegram source status");
    }
  };

  const handleDeleteChannel = async (id: number, channelName: string) => {
    if (!confirm(`Are you sure you want to delete @${channelName}?`)) return;

    setError(null);
    setSuccess(null);
    try {
      await apiService.deleteTelegramSource(id);
      setSources((prev) => prev.filter((s) => s.id !== id));
      setSuccess(`Channel @${channelName} deleted successfully.`);
    } catch (err: any) {
      setError(err.message || "Failed to delete Telegram source");
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Add source form */}
      <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-card/40 flex flex-col gap-4">
        <div>
          <h2 className="text-sm font-bold text-white">Add Monitored Telegram Source</h2>
          <p className="text-11 text-gray-400 mt-1">
            Specify public Telegram channels or groups to monitor for fresh job listing aggregation.
          </p>
        </div>

        <form onSubmit={handleAddChannel} className="flex gap-3 mt-1">
          <div className="relative flex-1">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 font-bold text-sm">@</span>
            <input
              type="text"
              placeholder="e.g. freshers_opening or reactjobs"
              value={newChannel}
              onChange={(e) => setNewChannel(e.target.value)}
              disabled={actionLoading}
              className="w-full bg-background border border-gray-800 focus:border-purple-500/80 rounded-xl py-2.5 pl-8 pr-4 text-xs text-white placeholder-gray-600 focus:outline-none transition-all"
            />
          </div>
          <button
            type="submit"
            disabled={actionLoading || !newChannel.trim()}
            className="bg-purple-600 hover:bg-purple-500 disabled:bg-gray-800 disabled:text-gray-600 text-white font-bold text-xs px-5 py-2.5 rounded-xl flex items-center gap-2 transition-all cursor-pointer select-none"
          >
            {actionLoading ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
            <span>Add Channel</span>
          </button>
        </form>

        {/* Feedback alerts */}
        {error && (
          <div className="flex items-center gap-2.5 text-xs text-red-400 bg-red-950/15 border border-red-900/35 p-3 rounded-xl">
            <AlertCircle size={14} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="flex items-center gap-2.5 text-xs text-emerald-400 bg-emerald-950/15 border border-emerald-900/35 p-3 rounded-xl">
            <Check size={14} className="shrink-0" />
            <span>{success}</span>
          </div>
        )}
      </div>

      {/* Sources list */}
      <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-card/40 flex flex-col gap-4">
        <div className="flex justify-between items-center border-b border-gray-800 pb-3">
          <h2 className="text-sm font-bold text-white">Monitored Channel Sources</h2>
          <button
            onClick={fetchSources}
            title="Refresh sources"
            className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-gray-800/40 transition-colors"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {loading ? (
          <div className="text-center py-10 text-xs text-gray-500 flex justify-center items-center gap-2">
            <RefreshCw size={12} className="animate-spin" />
            <span>Loading active Telegram channels...</span>
          </div>
        ) : sources.length === 0 ? (
          <div className="text-center py-10 text-xs text-gray-500 italic">
            No Telegram sources added yet. Seed default is 'freshers_opening'.
          </div>
        ) : (
          <div className="flex flex-col gap-2.5">
            {sources.map((src) => (
              <div
                key={src.id}
                className="flex items-center justify-between p-3.5 rounded-xl border border-gray-800/40 bg-muted/40 hover:border-gray-850 hover:bg-muted/60 transition-all"
              >
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-bold text-white">@{src.channel_name}</span>
                  <span className="text-9 text-gray-500">
                    Last checked:{" "}
                    {src.last_checked
                      ? new Date(src.last_checked).toLocaleString()
                      : "Never"}
                  </span>
                </div>

                <div className="flex items-center gap-3.5">
                  {/* Active Toggle Switch */}
                  <button
                    onClick={() => handleToggleActive(src)}
                    title={src.active ? "Disable channel" : "Enable channel"}
                    className="text-gray-400 hover:text-white transition-colors cursor-pointer"
                  >
                    {src.active ? (
                      <div className="flex items-center gap-1.5 text-10 text-emerald-400 font-bold bg-emerald-950/20 border border-emerald-900/40 px-2.5 py-1 rounded-lg">
                        <ToggleRight size={14} className="text-emerald-400" />
                        <span>Active</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-10 text-gray-500 font-bold bg-gray-900/30 border border-gray-800 px-2.5 py-1 rounded-lg">
                        <ToggleLeft size={14} className="text-gray-600" />
                        <span>Disabled</span>
                      </div>
                    )}
                  </button>

                  {/* Delete Button */}
                  <button
                    onClick={() => handleDeleteChannel(src.id, src.channel_name)}
                    title="Delete source"
                    className="p-1.5 rounded-lg border border-transparent hover:border-red-900/30 hover:bg-red-950/15 text-gray-500 hover:text-red-400 transition-all cursor-pointer"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
