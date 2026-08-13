import bootstrap  # noqa: F401

from asset_view_builder import build_asset_views
from daily_briefing_builder import build_daily_briefings
from issue_flow_builder import build_issue_flows
from news_event_builder import build_news_events
from region_risk_builder import build_region_risks


def rebuild_all_views(limit_dates: int = 14) -> None:
    build_daily_briefings(limit_dates=limit_dates)
    build_issue_flows()
    build_asset_views()
    build_news_events()
    build_region_risks()


if __name__ == "__main__":
    rebuild_all_views()
