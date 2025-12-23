# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import json
import logging

import azure.functions as func

from shared.database import RESOURCE_FIELDS
from shared.utils import (
    create_error_response,
    get_latest_versions,
    sanitize_version,
)


def register_function(app, collection):
    """Register the function with the app."""

    @app.function_name(name="list_all_resources")
    @app.route(
        route="resources/list-all-resources",
        auth_level=func.AuthLevel.ANONYMOUS,
    )
    def list_all_resources(req: func.HttpRequest) -> func.HttpResponse:
        """
        Get all resources where a gem5 version in the resource is a prefix
        of the specified version parameter.

        Route: /resources/list-all-resources

        Query Parameters:
        - gem5-version: Required, the gem5 version to match against
                        (e.g., "25.0.0.1" will match resources with "25.0")
        - latest-version: Optional, if set to "true", returns only the latest
                          compatible version of each resource instead of all
                          compatible versions. Default is false (return all).
        """
        logging.info(
            "Processing request to list all resources by gem5 version"
        )
        try:
            gem5_version = req.params.get("gem5-version")
            latest_version_only = (
                req.params.get("latest-version", "false").lower() == "true"
            )

            if not gem5_version:
                return create_error_response(
                    400, "'gem5-version' parameter is required"
                )

            gem5_version = sanitize_version(gem5_version)

            if not gem5_version:
                return create_error_response(
                    400, "Invalid 'gem5-version' parameter format"
                )

            # Build a list of all possible prefixes from the version
            # Starting from major.minor since gem5 versions always have at
            # least one dot (e.g., "25.0", "23.1")
            # e.g., "25.0.0.1" -> ["25.0", "25.0.0", "25.0.0.1"]
            version_parts = gem5_version.split(".")
            prefixes = []
            for i in range(2, len(version_parts) + 1):
                prefixes.append(".".join(version_parts[:i]))

            # If only one part provided (e.g., "25"), return error
            if not prefixes:
                return create_error_response(
                    400,
                    "Invalid 'gem5-version' parameter: must have at least "
                    "major version format (e.g., '23.0', '25.1')",
                )

            # Query for resources where any gem5_version matches one of
            # the prefixes
            query = {"gem5_versions": {"$in": prefixes}}

            resources = list(collection.find(query, RESOURCE_FIELDS))

            # If latest-version is set, return only the latest version of
            # each resource
            if latest_version_only:
                resources = get_latest_versions(resources)

            return func.HttpResponse(
                body=json.dumps(resources),
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

        except Exception as e:
            logging.error(f"Error listing resources by gem5 version: {str(e)}")
            return create_error_response(500, "Internal server error")
