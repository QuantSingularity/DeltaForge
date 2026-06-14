import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

// Subscribes to the live snapshot stream over WebSocket and falls back to REST
// polling if the socket is unavailable. Returns { state, connected }.
export function useLiveState() {
  const [state, setState] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    let closed = false;

    const startPolling = () => {
      if (pollRef.current) return;
      const tick = async () => {
        try {
          setState(await api.state());
        } catch {
          /* server not ready yet */
        }
      };
      tick();
      pollRef.current = setInterval(tick, 2500);
    };

    const stopPolling = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    const connect = () => {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(`${proto}://${location.host}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (closed) return;
        setConnected(true);
        stopPolling();
      };
      ws.onmessage = (ev) => {
        try {
          setState(JSON.parse(ev.data));
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onclose = () => {
        if (closed) return;
        setConnected(false);
        startPolling();
        setTimeout(connect, 3000); // reconnect with backoff
      };
      ws.onerror = () => ws.close();
    };

    connect();
    startPolling(); // immediate data while the socket handshakes

    return () => {
      closed = true;
      stopPolling();
      wsRef.current?.close();
    };
  }, []);

  return { state, connected };
}
