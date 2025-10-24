import React, { useEffect, useMemo, useState } from "react";
import { API_BASE } from "../lib/api";

function buildWsUrl() {
  try {
    const url = new URL(API_BASE);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/ws/stream";
    return url.toString();
  } catch (error) {
    return "ws://localhost:8000/ws/stream";
  }
}

export function LogPane() {
  const [messages, setMessages] = useState([]);
  const wsUrl = useMemo(() => buildWsUrl(), []);

  useEffect(() => {
    const socket = new WebSocket(wsUrl);
    socket.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
        setMessages((prev) => [...prev.slice(-99), payload]);
      } catch (err) {
        console.warn("Failed to parse WS message", err);
      }
    });
    return () => socket.close();
  }, [wsUrl]);

  return (
    <section className="panel log-panel">
      <h2 className="panel-title">Live Log</h2>
      <ul className="log-list">
        {messages.map((entry, index) => (
          <li key={index}>
            <span className="log-topic">[{entry.topic}]</span> {JSON.stringify(entry.payload)}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default LogPane;
