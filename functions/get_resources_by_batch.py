import azure.functions as func
import logging
import json
from urllib.parse import parse_qs
from shared.utils import create_error_response, sanitize_id, sanitize_version
from shared.database import RESOURCE_FIELDS

def register_function(app, collection):
    """Register the function with the app."""
    
    @app.function_name(name="get_resources_by_batch")
    @app.route(route="resources/find-resources-in-batch", auth_level=func.AuthLevel.ANONYMOUS)
    def get_resources_by_batch(req: func.HttpRequest) -> func.HttpResponse:
        """
        Get multiple resources by their IDs and versions.

        Route: /resources/find-resources-in-batch

        Query Parameters:
        - id: Required, can appear multiple times (up to 40)
        - resource_version: Required, must match number of id parameters and be in same order
                If "None" is passed, all versions of the resource with the corresponding ID will be returned
        """
        logging.info('Processing request to get resources by batch')
        try:
            query_params = parse_qs(req.url.split('?', 1)[1] if '?' in req.url else '')
            ids = [sanitize_id(i) for i in query_params.get('id', [])]
            versions = [None if v.lower() == "none" else sanitize_version(v) 
                      for v in query_params.get('resource_version', [])]

            # Validate inputs
            if not ids or any(i is None for i in ids):
                return create_error_response(400, "At least one valid 'id' parameter is required")

            if len(versions) != len(ids):
                return create_error_response(400, "Each 'id' parameter must have a corresponding 'resource_version' parameter (use 'None' to fetch all versions)")
            
            # Create a list of queries for MongoDB $or operator
            queries = []
            for id, version in zip(ids, versions):
                if version is None:
                    # If version is None, find all resources with this id
                    queries.append({"id": id})
                else:
                    # Otherwise, find the specific version
                    queries.append({"id": id, "resource_version": version})

            resources = list(collection.find({"$or": queries}, RESOURCE_FIELDS))

            # Check if any resources were found
            if not resources:
                return create_error_response(404, "No requested resources were found")
            
            # Check if at least one instance of each requested ID is present
            found_ids = set(resource.get("id") for resource in resources)
            missing_ids = set(ids) - found_ids
            
            if missing_ids:
                return create_error_response(
                    404, 
                    f"The following requested resources were not found: {', '.join(missing_ids)}"
                )

            return func.HttpResponse(
                body=json.dumps(resources),
                status_code=200,
                headers={"Content-Type": "application/json"}
            )

        except Exception as e:
            logging.error(f"Error fetching resources by batch: {str(e)}")
            return create_error_response(500, "Internal server error")