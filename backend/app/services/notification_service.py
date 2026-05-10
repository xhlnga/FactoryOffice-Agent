import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.integration import IntegrationMessage, get_integration_adapter

_logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)


def notify(message: IntegrationMessage) -> None:
    """Fire-and-forget async notification. Errors are logged, never raised."""
    if not settings.integration_enabled:
        return
    adapter = get_integration_adapter(settings.integration_platform)
    if adapter is None:
        return
    _executor.submit(_send_and_log, adapter, message)


def _send_and_log(adapter, message: IntegrationMessage) -> None:
    try:
        if not adapter.send(message):
            _logger.warning("Notification send returned failure via %s", adapter.platform_name)
    except Exception:
        _logger.exception("Notification failed via %s", adapter.platform_name)
