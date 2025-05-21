import azure.functions as func
import logging
import json
from bson import json_util
from shared.utils import create_error_response, sanitize_id, sanitize_version
from shared.database import RESOURCE_FIELDS

def register_function(app, collection):
    """Register the function with the app."""
    
    @app.function_name(name="get_resource_by_id")
    @app.route(route="resources/find-resource-by-id", auth_level=func.AuthLevel.ANONYMOUS)
    def get_resource_by_id(req: func.HttpRequest) -> func.HttpResponse:
        """
        Get a resource by ID with optional version filter.

        Route: /resources/{resource_id}

        Query Parameters:
        - resource_id: Required. The id of the resource to find.
        - resource_version: Optional. If provided, returns only the resource with matching ID and version.
        """

        logging.info('Processing request to get resource by ID')
        try:
            # Get the resource ID from the route parameter
            resource_id = sanitize_id(req.params.get('id'))
            if not resource_id:
                return create_error_response(400, "Resource ID is required and must be alphanumeric, dash, underscore, or dot.")

            # Get optional resource version from query parameters
            resource_version = req.params.get('resource_version')
            if resource_version:
                resource_version = sanitize_version(resource_version)
                if not resource_version:
                    return create_error_response(400, "Invalid resource_version format.")

            # Create query
            query = {"id": resource_id}
            if resource_version:
                query["resource_version"] = resource_version

            resource = list(collection.find(query, RESOURCE_FIELDS))

            if not resource:
                return create_error_response(404, f"Resource with ID '{resource_id}' not found")

            return func.HttpResponse(
                body=json.dumps(resource, default=json_util.default),
                headers={"Content-Type": "application/json"},
                status_code=200
            )

        except Exception as e:
            logging.error(f"Error fetching resource by ID: {str(e)}")
            return create_error_response(500, "Internal server error")