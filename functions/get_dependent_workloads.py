# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import azure.functions as func
import logging
import json
from shared.utils import create_error_response, sanitize_id

def register_function(app, collection):
    """Register the function with the app."""
    
    @app.route(route="resources/get-dependent-workloads", auth_level=func.AuthLevel.ANONYMOUS)
    def get_dependent_workloads(req: func.HttpRequest) -> func.HttpResponse:
        """
        Find workloads that depend on a specified resource ID.

        Route: /resources/dependent-workloads

        Query Parameters:
        - id: Required. The resource ID to find dependent workloads for.
        
        Returns:
        - A list of workload that depend on the specified resource.
        """
        logging.info('Processing request to find dependent workloads')
        
        try:
            # Get required resource ID parameter
            resource_id = sanitize_id(req.params.get('id'))
            if not resource_id:
                return create_error_response(400, "Missing or invalid required parameter 'id'")
            
            # Build pipeline to find dependent workloads
            pipeline = [
                {
                    "$match": {
                        "category": "workload"
                    }
                },
                {
                    "$addFields": {
                        "resources": {
                            "$objectToArray": "$resources"
                        }
                    }
                },
                {
                    "$unwind": "$resources"
                },
                {
                    "$match": {
                        "resources.v": resource_id
                    }
                },
                {
                    "$group": {
                        "_id": "$id",
                    }
                }
            ]
            
            # Execute the pipeline
            workloads = list(collection.aggregate(pipeline))
            
            return func.HttpResponse(
                body=json.dumps(workloads),
                headers={"Content-Type": "application/json"},
                status_code=200
            )
            
        except Exception as e:
            logging.error(f"Error finding dependent workloads: {str(e)}")
            return create_error_response(500, "Internal server error")