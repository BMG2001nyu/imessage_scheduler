"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useWebSocket } from "@/lib/use-websocket";
import { ScheduleForm } from "@/components/schedule-form";
import { MessageList } from "@/components/message-list";
import { Loader2, Wifi, WifiOff } from "lucide-react";
import type { Message } from "@/lib/api";

export default function SchedulerPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState(false);

  const fetchMessages = useCallback(async () => {
    try {
      const data = await api.listMessages({ limit: 100 });
      setMessages(data.messages);
      setTotal(data.total);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  const { connected } = useWebSocket(
    useCallback(
      (event) => {
        const msg = event.data;
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === msg.id);
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = msg;
            return updated;
          }
          if (event.event === "message_created") {
            return [msg, ...prev];
          }
          return prev;
        });
      },
      []
    )
  );

  return (
    <div className="space-y-8">
      <div className="text-center mb-2">
        <h1 className="text-2xl font-bold text-foreground">Schedule a Message</h1>
        <p className="text-sm text-muted mt-1">
          Compose and schedule iMessages to be sent automatically
        </p>
      </div>

      <ScheduleForm onCreated={fetchMessages} />

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            Scheduled Messages
            <span className="text-muted font-normal">({total})</span>
          </h2>
          <div className="flex items-center gap-1.5 text-xs text-muted" title={connected ? "Live updates active" : "Reconnecting..."}>
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

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <p className="text-sm text-red-500 mb-2">Failed to load messages</p>
            <button
              onClick={fetchMessages}
              className="text-sm text-primary hover:underline cursor-pointer"
            >
              Try again
            </button>
          </div>
        ) : (
          <MessageList messages={messages} onRefresh={fetchMessages} />
        )}
      </div>
    </div>
  );
}
