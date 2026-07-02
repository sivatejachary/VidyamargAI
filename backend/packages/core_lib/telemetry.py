import logging
import json
import sys
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """
    Structured logging formatter returning records in JSON format.
    """
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "file": record.filename,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        if hasattr(record, "context"):
            log_data["context"] = getattr(record, "context")
            
        return json.dumps(log_data)


def configure_telemetry(service_name: str, debug_mode: bool = False):
    """
    Configures the root logging stream using structured JSON format.
    """
    root_logger = logging.getLogger()
    level = logging.DEBUG if debug_mode else logging.INFO
    root_logger.setLevel(level)
    
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(service_name))
    root_logger.addHandler(handler)
    
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logger = logging.getLogger("packages.core_lib.telemetry")
    logger.info(f"Structured telemetry configured for service: {service_name}")
