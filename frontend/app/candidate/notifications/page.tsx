"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { Bell, CheckCircle, Award, AlertCircle, Info } from "lucide-react";

interface Notification {
  id: number;
  message: string;
  created_at: string;
  type?: string;
}

export default function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  const loadNotifications = async () => {
    try {
      const data = await apiService.getNotifications();
      setNotifications(data || []);
    } catch (err) {
      console.error(err);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const getIcon = (type?: string) => {
    switch (type) {
      case "check": return <CheckCircle className="text-emerald-500" size={16} />;
      case "alert": return <AlertCircle className="text-amber-500" size={16} />;
      case "award": return <Award className="text-purple-500" size={16} />;
      default: return <Info className="text-blue-500" size={16} />;
    }
  };

  return (
    <div className="w-full min-h-screen bg-background p-6 font-sans text-foreground transition-colors duration-300">
      
      {/* Header */}
      <div className="border-b border-border pb-5 mb-6">
        <h1 className="text-xl font-bold tracking-tight text-foreground">Notifications</h1>
      </div>

      <div className="max-w-3xl mx-auto flex flex-col gap-3">
        {loading ? (
          <div className="flex flex-col gap-3">
            <div className="h-16 bg-card border border-border rounded-2xl animate-pulse" />
            <div className="h-16 bg-card border border-border rounded-2xl animate-pulse" />
          </div>
        ) : notifications.length === 0 ? (
          <div className="bg-card border border-border rounded-3xl p-12 text-center text-gray-400 shadow-sm">
            <Bell size={36} className="mx-auto text-gray-300 dark:text-gray-700 mb-2" />
            <p className="text-xs">All caught up! No new notifications.</p>
          </div>
        ) : (
          notifications.map((notif) => (
            <div 
              key={notif.id}
              className="bg-card border border-border rounded-2xl p-4.5 flex gap-4 items-start shadow-sm hover:border-primary/20 transition-colors"
            >
              <div className="p-2.5 rounded-xl bg-muted border border-border shrink-0">
                {getIcon(notif.type)}
              </div>
              <div className="flex-1">
                <p className="text-xs font-semibold text-foreground leading-relaxed">
                  {notif.message}
                </p>
                <span className="text-10 text-gray-400 mt-1.5 block">
                  {new Date(notif.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

    </div>
  );
}
