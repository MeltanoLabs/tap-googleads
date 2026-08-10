"""Stream type classes for tap-googleads."""

from __future__ import annotations

import functools
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from singer_sdk import typing as th  # JSON Schema typing helpers

from tap_googleads._gaql import GAQL
from tap_googleads.client import GoogleAdsStream, ResumableAPIError

if TYPE_CHECKING:
    import requests
    from singer_sdk.helpers.types import Context, Record

SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")


class AccessibleCustomers(GoogleAdsStream):
    """Accessible Customers."""

    http_method = "GET"
    path = "/customers:listAccessibleCustomers"
    name = "accessible_customers"
    primary_keys = ("resourceNames",)
    replication_key = None
    schema = th.PropertiesList(
        th.Property("resourceNames", th.ArrayType(th.StringType)),
    ).to_dict()

    def generate_child_contexts(
        self,
        record: Record,
        context: Context | None,
    ) -> Iterable[Context | None]:
        """Generate child contexts.

        Args:
            record: Individual record in the stream.
            context: Stream partition or context dictionary.

        Yields:
            A child context for each child stream.

        """
        for customer in record.get("resourceNames", []):
            customer_id = customer.split("/")[1]
            yield {"customer_id": customer_id}


class CustomerHierarchyStream(GoogleAdsStream):
    """Customer Hierarchy.

    Inspiration from Google here
    https://developers.google.com/google-ads/api/docs/account-management/get-account-hierarchy.

    This stream is strictly to be the Parent Stream, to let all Child Streams
    know when to query the down stream apps.

    """

    @functools.cached_property
    def gaql(self) -> GAQL:
        return GAQL(
            "customer_client.client_customer",
            "customer_client.level",
            "customer_client.status",
            "customer_client.manager",
            "customer_client.descriptive_name",
            "customer_client.currency_code",
            "customer_client.time_zone",
            "customer_client.id",
            from_table="customer_client",
            where_clause=[
                "customer_client.level <= 1",
            ],
        )

    records_jsonpath = "$.results[*]"
    name = "customer_hierarchy"
    primary_keys = ("customerClient__id",)
    replication_key = None
    parent_stream_type = AccessibleCustomers
    schema = th.PropertiesList(
        th.Property("customer_id", th.StringType),
        th.Property("parent_customer_id", th.StringType),
        th.Property(
            "customerClient",
            th.ObjectType(
                th.Property("resourceName", th.StringType),
                th.Property("clientCustomer", th.StringType),
                th.Property("level", th.StringType),
                th.Property("status", th.StringType),
                th.Property("timeZone", th.StringType),
                th.Property("manager", th.BooleanType),
                th.Property("descriptiveName", th.StringType),
                th.Property("currencyCode", th.StringType),
                th.Property("id", th.StringType),
            ),
        ),
    ).to_dict()

    seen_customer_ids: set[str] = set()

    def validate_response(self, response: requests.Response):
        if response.status_code == HTTPStatus.FORBIDDEN:
            msg = self.response_error_message(response)
            raise ResumableAPIError(msg, response)

        super().validate_response(response)

    def generate_child_contexts(self, record, context):
        customer_ids = self.customer_ids

        if customer_ids is None:
            customer = record["customerClient"]

            if customer["manager"]:
                self.logger.warning(
                    "%s is a manager, skipping",
                    customer["clientCustomer"],
                )
                return

            if customer["status"] != "ENABLED":
                self.logger.warning(
                    "%s is not enabled, skipping",
                    customer["clientCustomer"],
                )
                return

            customer_ids = {customer["id"]}

        # sync only customers we haven't seen
        customer_ids = set(customer_ids) - self.seen_customer_ids

        for customer_id in customer_ids:
            customer_context = {"customer_id": customer_id}
            # Add parent manager account id if this is a child
            if customer_id != context["customer_id"]:
                customer_context["parent_customer_id"] = context["customer_id"]
            yield customer_context

        self.seen_customer_ids.update(customer_ids)


class ReportsStream(GoogleAdsStream):
    parent_stream_type = CustomerHierarchyStream
