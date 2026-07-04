from __future__ import annotations

import json

from prefect import flow, task

from ml.pipeline.live_market import refresh_with_app_database


@task(retries=2, retry_delay_seconds=30)
def refresh_market_task() -> dict[str, object]:
    return refresh_with_app_database().as_dict()


@flow(name="live-market-refresh", log_prints=True)
def live_market_flow() -> dict[str, object]:
    result = refresh_market_task()
    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    # Refresh once on container start, then register the hourly deployment and stay alive.
    live_market_flow()
    live_market_flow.serve(name="hourly-live-market", cron="17 * * * *")
