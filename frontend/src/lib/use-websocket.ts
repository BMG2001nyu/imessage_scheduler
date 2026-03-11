"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { Message } from "./api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8002";

interface WSEvent {
  event: string;
  data: Message;
}

type EventHandler = (event: WSEvent) => void;

export function useWebSocket(onEvent: EventHandler) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlerRef = useRef(onEvent);
  const [connected, setConnected] = useState(false);

  handlerRef.current = onEvent;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_URL}/ws/updates`);

    ws.onopen = () => setConnected(true);

    ws.onmessage = (evt) => {
      try {
        const parsed: WSEvent = JSON.parse(evt.data);
        handlerRef.current(parsed);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();

    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected };
}
