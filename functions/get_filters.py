import azure.functions as func
import logging
import json
from bson import json_util
from shared.utils import create_error_response

def register_function(app, collection):
    """Register the function with the app."""
    
    @app.route(route="resources/filters", auth_level=func.AuthLevel.ANONYMOUS)
    def get_filters(req: func.HttpRequest) -> func.HttpResponse:
        """
        Get distinct categories, architectures, and gem5 versions from the resources collection.

        Route: /resources/filters

        No query parameters required for this endpoint.
        """
        logging.info('Processing request to get resource filters')
        try:
            # Build the aggregation pipeline to get distinct values
            pipeline = [
                {
                    "$unwind": {
                        "path": "$gem5_versions",
                        "preserveNullAndEmptyArrays": True
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "category": {"$addToSet": "$category"},
                        "architecture": {"$addToSet": "$architecture"},
                        "gem5_versions": {"$addToSet": "$gem5_versions"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "category": 1,
                        "architecture": 1,
                        "gem5_versions": 1
                    }
                }
            ]
            
            # Execute the aggregation
            results = list(collection.aggregate(pipeline))
            
            # If no results, return empty arrays
            if not results:
                return func.HttpResponse(
                    body=json.dumps({
                        "category": [],
                        "architecture": [],
                        "gem5_versions": []
                    }),
                    headers={"Content-Type": "application/json"},
                    status_code=200
                )
            
            # Process the results
            filters = results[0]
            
            # Filter out null values from architecture
            if "architecture" in filters:
                filters["architecture"] = [a for a in filters["architecture"] if a is not None]
            
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
                status_code=200
            )

        except Exception as e:
            logging.error(f"Error getting resource filters: {str(e)}")
            return create_error_response(500, "Internal server error")