import { createServer } from "http";
import { WebSocketServer, WebSocket } from "ws";

import app from "./app.js";
import { env } from "./config/env.js";
import { startBackgroundSchedulers } from "./scheduler/cronRunner.js";

const server = createServer(app);

const wss = new WebSocketServer({
  server,
  path: "/ws",
});

const activeWsClients = new Map<string, WebSocket>();

wss.on("connection", (ws, req) => {
  const urlParts = req.url?.split("/") || [];
  const candidateId = urlParts[urlParts.length - 1] || "anonymous";

  activeWsClients.set(candidateId, ws);
  console.log(`[WebSocket] Client connected: ${candidateId}`);

  ws.on("close", () => {
    activeWsClients.delete(candidateId);
    console.log(`[WebSocket] Client disconnected: ${candidateId}`);
  });
});

if (env.NODE_ENV !== "production") {
  startBackgroundSchedulers();
}

server.listen(env.PORT, () => {
  console.log(`[Server] VidyaMarg Node backend running on ${env.PORT}`);
});
