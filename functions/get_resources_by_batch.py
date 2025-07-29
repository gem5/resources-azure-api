# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import json
import logging

import azure.functions as func

from shared.database import RESOURCE_FIELDS
from shared.utils import (
    create_error_response,
    sanitize_id,
    sanitize_version,
)


def register_function(app, collection):
    """Register the function with the app."""

    @app.function_name(name="find_resources_in_batch")
    @app.route(
        route="resources/find-resources-in-batch",
        auth_level=func.AuthLevel.ANONYMOUS,
    )
    def find_resources_in_batch(req: func.HttpRequest) -> func.HttpResponse:
        """
        Get multiple resources by their IDs and versions.

        Route: /resources/find-resources-in-batch

        Query Parameters:
        - id: Required, can appear multiple times (up to 40)
        - resource_version: Required, must match number of id parameters and
                            be in same order.
                            If "None" is passed, all versions of the resource
                            with the corresponding ID will be returned.
        """
        logging.info("Processing request to get resources by batch")
        try:

            if not "id" in req.params.keys():
                return create_error_response(
                    400, "At least one valid 'id' parameter is required"
                )

            ids = [sanitize_id(i) for i in req.params.get("id").split(",")]

            if not "resource_version" in req.params.keys():
                return create_error_response(
                    400,
                    "Each 'id' parameter must have a corresponding "
                    "'resource_version' parameter "
                    "(use 'None' to fetch all versions)",
                )

            versions = [
                None if v.lower() == "none" else sanitize_version(v)
                for v in req.params.get("resource_version").split(",")
            ]

            if len(versions) != len(ids):
                return create_error_response(
                    400,
                    "Each 'id' parameter must have a corresponding "
                    "'resource_version' parameter "
                    "(use 'None' to fetch all versions)",
                )

            # Create a list of queries for MongoDB $or operator
            queries = []
            for id, version in zip(ids, versions):
                if version is None:
                    # If version is None, find all resources with this id
                    queries.append({"id": id})
                else:
                    # Otherwise, find the specific version
                    queries.append({"id": id, "resource_version": version})

            resources = list(
                collection.find({"$or": queries}, RESOURCE_FIELDS)
            )

            return func.HttpResponse(
                body=json.dumps(resources),
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

        except Exception as e:
            logging.error(f"Error fetching resources by batch: {str(e)}")
            return create_error_response(500, "Internal server error")
