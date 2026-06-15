import { useEffect, useRef, useState } from "react";

export const useWebSockets = (clientId: string) => {
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const listeners = useRef<((event: any) => void)[]>([]);

  useEffect(() => {
    if (!clientId) return;

    const getWsUrl = () => {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }

  if (typeof window !== "undefined") {
    let host = window.location.hostname;

    if (host === "localhost") {
      host = "127.0.0.1";
    }

    return `ws://${host}:8000/ws`;
  }

  return "ws://vidyamargai-production.up.railway.app/ws";
};
    const WS_URL = getWsUrl();
    const socket = new WebSocket(`${WS_URL}/${clientId}`);

    socket.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected:", clientId);
    };

    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        listeners.current.forEach((cb) => cb(parsed));
      } catch (err) {
        console.error("Failed to parse socket packet:", err);
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      console.log("WebSocket disconnected:", clientId);
    };

    ws.current = socket;

    return () => {
      socket.close();
    };
  }, [clientId]);

  const addMessageListener = (callback: (event: any) => void) => {
    listeners.current.push(callback);
    return () => {
      listeners.current = listeners.current.filter((cb) => cb !== callback);
    };
  };

  const sendMessage = (msg: any) => {
    if (ws.current && isConnected) {
      ws.current.send(JSON.stringify(msg));
    }
  };

  return { isConnected, addMessageListener, sendMessage };
};
