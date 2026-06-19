import asyncio
import logging
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.mcp_models import AgentHealth, MCPAuditLog, DeadLetterJob
from app.core.queue import is_redis_connected

logger = logging.getLogger("app.services.alerting")

# Simulated Alert Dispatchers
def send_telegram_alert(message: str):
    logger.warning(f"[TELEGRAM ALERT SHIPPED] {message}")

def send_whatsapp_alert(message: str):
    logger.warning(f"[WHATSAPP ALERT SHIPPED] {message}")

def send_critical_system_alert(message: str):
    logger.error(f"[CRITICAL ALERT SHIPPED] {message}")

def check_alerting_rules():
    """Evaluates all operational alert thresholds."""
    with SessionLocal() as db:
        # Rule 1: Agent unhealthy > 5 min -> Telegram
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        unhealthy_agents = db.query(AgentHealth).filter(
            (AgentHealth.status.in_(["unhealthy", "degraded"])) |
            (AgentHealth.last_heartbeat < five_min_ago)
        ).all()
        for agent in unhealthy_agents:
            # Check if indeed heartbeat is older than 5 mins
            if agent.last_heartbeat < five_min_ago:
                send_telegram_alert(
                    f"Agent '{agent.agent_name}' has been unhealthy/dead since "
                    f"{agent.last_heartbeat.isoformat()} (older than 5 minutes)."
                )

        # Rule 2: DLQ > 10 jobs -> WhatsApp
        dlq_count = db.query(DeadLetterJob).filter(DeadLetterJob.status == "pending").count()
        if dlq_count > 10:
            send_whatsapp_alert(
                f"Dead Letter Queue contains {dlq_count} pending failed background jobs (threshold: 10)."
            )

        # Rule 3: Redis disconnected -> Critical Alert
        if not is_redis_connected():
            send_critical_system_alert("Redis database disconnected! Application fell back to database queue mode.")

        # Rule 4: MCP latency P95 > 1000ms -> Warning (only for successful calls, min 10 samples)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        logs = db.query(MCPAuditLog.latency).filter(
            MCPAuditLog.created_at >= twenty_four_hours_ago,
            MCPAuditLog.status == "success"
        ).all()
        latencies = [l[0] for l in logs]
        if len(latencies) >= 10:
            sorted_latencies = sorted(latencies)
            idx = int((len(sorted_latencies) - 1) * 0.95)
            p95 = sorted_latencies[idx]
            if p95 > 1000:
                logger.warning(
                    f"[WARNING ALERT SHIPPED] MCP Tool calls P95 latency is {p95:.1f}ms "
                    f"exceeding 1000ms threshold."
                )

async def start_alert_coordinator():
    """Background loop to periodically run operational rules check."""
    logger.info("Operational Alerting coordinator worker started.")
    while True:
        try:
            check_alerting_rules()
        except Exception as e:
            logger.error(f"Error in alert coordinator check: {e}")
        await asyncio.sleep(10)
