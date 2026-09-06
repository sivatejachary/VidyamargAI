import express from "express";
import cors from "cors";
import { createServer } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { env } from "./config/env.js";
import { errorHandler } from "./middleware/errorHandler.js";
import { authRouter } from "./routes/auth.routes.js";
import { profileRouter } from "./routes/profile.routes.js";
import { jobAgentRouter } from "./routes/jobAgent.routes.js";
import { syncRouter } from "./routes/sync.routes.js";
import { startBackgroundSchedulers } from "./scheduler/cronRunner.js";

const app = express();
const server = createServer(app);
const wss = new WebSocketServer({ server, path: "/ws" });

const activeWsClients = new Map<string, WebSocket>();

wss.on("connection", (ws: WebSocket, req) => {
  const urlParts = req.url?.split("/") || [];
  const candidateId = urlParts[urlParts.length - 1] || "anonymous";

  activeWsClients.set(candidateId, ws);
  console.log(`[WebSocket] Client connected: candidate '${candidateId}'`);

  ws.on("close", () => {
    activeWsClients.delete(candidateId);
    console.log(`[WebSocket] Client disconnected: candidate '${candidateId}'`);
  });

  ws.on("message", (message) => {
    console.log(`[WebSocket message from ${candidateId}]:`, message.toString());
  });
});

const allowedOrigins = env.CORS_ORIGINS.split(",");
app.use(
  cors({
    origin: (origin, callback) => {
      if (!origin || allowedOrigins.includes(origin)) {
        callback(null, true);
      } else {
        callback(null, true);
      }
    },
    credentials: true,
  })
);

app.use(express.json({
  verify: (req: any, _res, buf) => {
    req.rawBody = buf.toString("utf-8");
  }
}));
app.use(express.urlencoded({ extended: true }));

app.get("/health", (_req, res) => {
  res.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    service: "vidyamarg-backend-node",
    version: "2.0.0",
  });
});

app.use("/api/v1/auth", authRouter);
app.use("/api/v1", profileRouter);
app.use("/api/v1", jobAgentRouter);
app.use("/api/v1", syncRouter);

app.use(errorHandler);

startBackgroundSchedulers();

server.listen(env.PORT, () => {
  console.log(`[Server] VidyaMarg AI Node.js Backend listening on port ${env.PORT} (Node ${process.version})`);
});
