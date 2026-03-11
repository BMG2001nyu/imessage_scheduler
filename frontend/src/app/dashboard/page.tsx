"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Clock,
  Send,
  CheckCircle2,
  XCircle,
  BarChart3,
  Phone,
  AlertCircle,
  Loader2,
  Zap,
  Wifi,
  WifiOff,
} from "lucide-react";
import { api } from "@/lib/api";
import { useWebSocket } from "@/lib/use-websocket";
import { StatusBadge } from "@/components/status-badge";
import { formatPhone, formatUpdatedTime } from "@/lib/format";
import type { Message, Stats } from "@/lib/api";

const STAT_CARDS = [
  { key: "queued" as const, label: "Queued", icon: Clock, color: "text-blue-600", bg: "bg-blue-50" },
  { key: "accepted" as const, label: "In Flight", icon: Zap, color: "text-amber-600", bg: "bg-amber-50" },
  { key: "sent" as const, label: "Sent", icon: Send, color: "text-green-600", bg: "bg-green-50" },
  { key: "delivered" as const, label: "Delivered", icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50" },
  { key: "failed" as const, label: "Failed", icon: XCircle, color: "text-red-600", bg: "bg-red-50" },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentMessages, setRecentMessages] = useState<Message[]>([]);
  const [failedMessages, setFailedMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [statsData, recentData, failedData] = await Promise.all([
        api.getStats(),
        api.listMessages({ limit: 20 }),
        api.listMessages({ status: "FAILED", limit: 10 }),
      ]);
      setStats(statsData);
      setRecentMessages(recentData.messages);
      setFailedMessages(failedData.messages);
    } catch {
      // silent - dashboard is read-only
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const { connected } = useWebSocket(
    useCallback(() => {
      fetchData();
    }, [fetchData])
  );

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-primary" />
            Dashboard
          </h1>
          <p className="text-sm text-muted mt-1">
            Overview of message scheduling and delivery
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted">
          {connected ? (
            <Wifi className="w-3.5 h-3.5 text-emerald-500" />
          ) : (
            <WifiOff className="w-3.5 h-3.5 text-red-400" />
          )}
          <span className={connected ? "text-emerald-600" : "text-red-400"}>
            {connected ? "Live" : "Offline"}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {STAT_CARDS.map(({ key, label, icon: Icon, color, bg }, i) => (
          <div
            key={key}
            className="bg-card rounded-xl border border-border p-4 animate-fade-in"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <div className={`w-8 h-8 rounded-lg ${bg} flex items-center justify-center mb-2`}>
              <Icon className={`w-4 h-4 ${color}`} />
            </div>
            <p className="text-2xl font-bold text-foreground tabular-nums">
              {stats?.[key] ?? 0}
            </p>
            <p className="text-xs text-muted">{label}</p>
          </div>
        ))}
      </div>

      {/* Total & Queue Depth */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-card rounded-xl border border-border p-5">
          <p className="text-sm text-muted mb-1">Total Messages</p>
          <p className="text-3xl font-bold text-foreground tabular-nums">{stats?.total ?? 0}</p>
        </div>
        <div className="bg-card rounded-xl border border-border p-5">
          <p className="text-sm text-muted mb-1">Queue Depth</p>
          <p className="text-3xl font-bold text-primary tabular-nums">
            {(stats?.queued ?? 0) + (stats?.accepted ?? 0)}
          </p>
          <p className="text-xs text-muted mt-0.5">
            {stats?.queued ?? 0} queued + {stats?.accepted ?? 0} in flight
          </p>
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-primary" />
          Recent Activity
        </h2>
        {recentMessages.length === 0 ? (
          <p className="text-sm text-muted py-8 text-center">No messages yet</p>
        ) : (
          <div className="space-y-2">
            {recentMessages.map((msg) => (
              <div
                key={msg.id}
                className="bg-card rounded-xl border border-border px-4 py-3 flex items-center gap-3 hover:shadow-sm transition-shadow"
              >
                <Phone className="w-4 h-4 text-primary flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium">{formatPhone(msg.phone_number)}</span>
                  <span className="text-muted text-xs ml-2 truncate">
                    {msg.body.length > 50 ? msg.body.slice(0, 50) + "..." : msg.body}
                  </span>
                </div>
                <StatusBadge status={msg.status} />
                <span className="text-xs text-muted flex-shrink-0 tabular-nums">
                  {formatUpdatedTime(msg.updated_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Failed Messages */}
      {failedMessages.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-red-600 mb-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            Failed Messages
          </h2>
          <div className="space-y-2">
            {failedMessages.map((msg) => (
              <div
                key={msg.id}
                className="bg-red-50/50 rounded-xl border border-red-100 px-4 py-3"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{formatPhone(msg.phone_number)}</span>
                  <span className="text-xs text-muted tabular-nums">
                    {msg.attempts}/{msg.max_attempts} attempts
                  </span>
                </div>
                <p className="text-sm text-foreground/70 mb-1 truncate">{msg.body}</p>
                {msg.failure_reason && (
                  <p className="text-xs text-red-600">{msg.failure_reason}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
