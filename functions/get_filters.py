# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import json
import logging

import azure.functions as func
from bson import json_util

from shared.utils import create_error_response


def register_function(app, collection, filter_values_collection):
    """Register the function with the app.

    Args:
        app: The Azure Functions app
        collection: The resources collection
        filter_values_collection: The materialized view collection for filter values
    """

    @app.route(route="resources/filters", auth_level=func.AuthLevel.ANONYMOUS)
    def get_filters(req: func.HttpRequest) -> func.HttpResponse:
        """
        Get distinct categories, architectures, and gem5 versions from the filter_values collection.

        Route: /resources/filters

        This function retrieves pre-computed filter values from a materialized view collection
        that is updated daily by a GitHub Action.
        """
        logging.info("Processing request to get resource filters")
        try:
            # Get the filter values from the materialized view collection
            cached_filters = filter_values_collection.find_one(
                {"_id": "current"}
            )

            if cached_filters and "filters" in cached_filters:
                filters = cached_filters["filters"]
                last_updated = cached_filters.get("timestamp")

                if last_updated:
                    logging.info(
                        f"Returning filter values last updated at {last_updated}"
                    )

                return func.HttpResponse(
                    body=json.dumps(filters, default=json_util.default),
                    headers={"Content-Type": "application/json"},
                    status_code=200,
                )
            else:
                logging.warning(
                    "No cached filter values found. Falling back to direct aggregation."
                )

                # Fallback to direct aggregation if the materialized view doesn't exist
                # This is the original aggregation pipeline
                pipeline = [
                    {
                        "$unwind": {
                            "path": "$gem5_versions",
                            "preserveNullAndEmptyArrays": True,
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                            "category": {"$addToSet": "$category"},
                            "architecture": {"$addToSet": "$architecture"},
                            "gem5_versions": {"$addToSet": "$gem5_versions"},
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                            "category": 1,
                            "architecture": 1,
                            "gem5_versions": 1,
                        }
                    },
                ]

                # Execute the aggregation
                results = list(collection.aggregate(pipeline))

                # If no results, return empty arrays
                if not results:
                    return func.HttpResponse(
                        body=json.dumps(
                            {
                                "category": [],
                                "architecture": [],
                                "gem5_versions": [],
                            }
                        ),
                        headers={"Content-Type": "application/json"},
                        status_code=200,
                    )

                # Process the results
                filters = results[0]

                # Filter out null values from architecture
                if "architecture" in filters:
                    filters["architecture"] = [
                        a for a in filters["architecture"] if a is not None
                    ]

                # Sort the arrays
                if "category" in filters:
                    filters["category"].sort()
                if "architecture" in filters:
                    filters["architecture"].sort()
                if "gem5_versions" in filters:
                    filters["gem5_versions"].sort(reverse=True)

                return func.HttpResponse(
                    body=json.dumps(filters, default=json_util.default),
                    headers={"Content-Type": "application/json"},
                    status_code=200,
                )

        except Exception as e:
            logging.error(f"Error getting resource filters: {str(e)}")
            return create_error_response(500, "Internal server error")
