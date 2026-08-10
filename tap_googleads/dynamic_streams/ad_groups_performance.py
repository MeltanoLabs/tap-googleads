"""AdGroupsPerformance for Google Ads tap."""

import functools

from tap_googleads._gaql import GAQL
from tap_googleads.dynamic_query_stream import DynamicQueryStream


class AdGroupsPerformance(DynamicQueryStream):
    """AdGroups Performance."""

    @functools.cached_property
    def gaql(self) -> GAQL:
        """The GAQL query for the AdGroupsPerformance stream."""
        return GAQL(
            "campaign.id",
            "campaign.resource_name",
            "ad_group.id",
            "ad_group.resource_name",
            "metrics.impressions",
            "metrics.clicks",
            "metrics.cost_micros",
            "metrics.conversions",
            "metrics.engagements",
            "metrics.interactions",
            "metrics.video_trueview_views",
            "metrics.conversions_value",
            "metrics.all_conversions",
            "metrics.all_conversions_value",
            "segments.date",
            from_table="ad_group",
            where_clause=[
                f"segments.date >= {self.start_date}",
                f"segments.date <= {self.end_date}",
            ],
        )

    name = "ad_groups_performance"
    primary_keys = ("campaign__id", "adGroup__id", "segments__date")
    replication_key = None
