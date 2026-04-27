import logging
import sys

from api_client import get_blocking

log = logging.getLogger(__name__)


def run(api_url: str, api_key: str, pipeline_run_id: str) -> None:
    log.info("Checking build gate for pipeline run %s", pipeline_run_id)
    is_blocking = get_blocking(api_url, api_key, pipeline_run_id)

    if is_blocking:
        log.error("Gate FAILED — blocking findings detected. Pipeline is blocked.")
        sys.exit(3)

    log.info("Gate PASSED — no blocking findings.")
    sys.exit(0)
