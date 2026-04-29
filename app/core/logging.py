import logging
import logging.handlers
import sys
from pathlib import Path
import structlog
from app.core.config import get_settings

def setup_logging():
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Ensure log directory exists
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    
    # 30-day rotating file handler (midnight rotation, keep 30)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=settings.log_dir / "echo_hq_server.log",
        when="midnight",
        interval=1,
        backupCount=30
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # Console structlog formatter
    structlog_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=True)
        ],
    )
    console_handler.setFormatter(structlog_formatter)
    
    # JSON formatter for file logs
    json_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer()
        ],
    )
    file_handler.setFormatter(json_formatter)
    
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Ensure model download logs are visible
    logging.getLogger("huggingface_hub").setLevel(logging.INFO)
    logging.getLogger("faster_whisper").setLevel(logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
