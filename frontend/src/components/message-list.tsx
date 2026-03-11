"use client";

import { useState } from "react";
import { Phone, Clock, X, Pencil, AlertCircle, MessageSquare, RotateCcw } from "lucide-react";
import type { Message } from "@/lib/api";
import { api } from "@/lib/api";
import { formatPhone, formatScheduledTime, formatRelativeTime, isOverdue } from "@/lib/format";
import { StatusBadge } from "./status-badge";
import { EditModal } from "./edit-modal";
import { showToast } from "./toast";

interface Props {
  messages: Message[];
  onRefresh: () => void;
}

export function MessageList({ messages, onRefresh }: Props) {
  const [cancelling, setCancelling] = useState<string | null>(null);
  const [editingMessage, setEditingMessage] = useState<Message | null>(null);

  const handleCancel = async (id: string) => {
    if (!confirm("Cancel this scheduled message?")) return;
    setCancelling(id);
    try {
      await api.cancelMessage(id);
      showToast("Message cancelled", "success");
      onRefresh();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to cancel";
      showToast(message, "error");
    } finally {
      setCancelling(null);
    }
  };

  if (messages.length === 0) {
    return (
      <div className="text-center py-16 animate-fade-in">
        <MessageSquare className="w-12 h-12 text-muted/30 mx-auto mb-3" />
        <p className="text-muted text-sm">No messages scheduled yet</p>
        <p className="text-muted/60 text-xs mt-1">
          Use the form above to schedule your first message
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {messages.map((msg, i) => (
          <div
            key={msg.id}
            className="bg-card rounded-xl border border-border p-4 hover:shadow-md transition-all animate-fade-in group"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <Phone className="w-4 h-4 text-primary flex-shrink-0" />
                  <span className="font-semibold text-sm">{formatPhone(msg.phone_number)}</span>
                  <StatusBadge status={msg.status} />
                  {msg.status === "QUEUED" && isOverdue(msg.scheduled_at) && (
                    <span className="text-[10px] font-medium text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
                      Due
                    </span>
                  )}
                </div>
                <p className="text-sm text-foreground/80 mb-2 line-clamp-2">{msg.body}</p>
                <div className="flex items-center gap-4 text-xs text-muted">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatScheduledTime(msg.scheduled_at)}
                  </span>
                  <span className="text-muted/40">|</span>
                  <span>{formatRelativeTime(msg.scheduled_at)}</span>
                  <span className="text-muted/40">{msg.timezone}</span>
                </div>
                {msg.failure_reason && (
                  <div className="flex items-start gap-1.5 mt-2 text-xs text-red-600 bg-red-50 rounded-lg px-2.5 py-1.5">
                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                    <span>{msg.failure_reason}</span>
                  </div>
                )}
                {msg.attempts > 1 && msg.status !== "FAILED" && (
                  <div className="flex items-center gap-1 mt-1.5 text-xs text-muted">
                    <RotateCcw className="w-3 h-3" />
                    <span>Attempt {msg.attempts} of {msg.max_attempts}</span>
                  </div>
                )}
              </div>

              {msg.status === "QUEUED" && (
                <div className="flex gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => setEditingMessage(msg)}
                    className="p-1.5 rounded-lg text-muted hover:text-primary hover:bg-primary/10 transition-colors cursor-pointer"
                    title="Edit message"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleCancel(msg.id)}
                    disabled={cancelling === msg.id}
                    className="p-1.5 rounded-lg text-muted hover:text-red-500 hover:bg-red-50 transition-colors cursor-pointer disabled:opacity-50"
                    title="Cancel message"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {editingMessage && (
        <EditModal
          message={editingMessage}
          onClose={() => setEditingMessage(null)}
          onSaved={() => {
            setEditingMessage(null);
            showToast("Message updated", "success");
            onRefresh();
          }}
        />
      )}
    </>
  );
}
