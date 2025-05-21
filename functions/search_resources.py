import azure.functions as func
import logging
import json
from bson import json_util
from shared.utils import (
    create_error_response, 
    sanitize_contains_str, 
    sanitize_must_include,
    sanitize_id
)

def register_function(app, collection):
    """Register the function with the app."""
    
    @app.function_name(name="search_resources")   
    @app.route(route="resources/search", auth_level=func.AuthLevel.ANONYMOUS)
    def search_resources(req: func.HttpRequest) -> func.HttpResponse:
        """
        Search resources with filtering capabilities.

        Route: /resources/search

        Query Parameters:
        - contains-str: Optional. The search term to find resources.
        - must-include: Optional. A CSV-formatted string defining filter criteria.
        - sort: Optional. Sort criteria ('date', 'name', 'version', 'id_asc', 'id_desc'). Default is score-based.
        - page: Optional. Page number for pagination (default: 1).
        - page-size: Optional. Number of results per page (default: 10).
        """
        logging.info('Processing request to search resources')
        try:
            # Get search query
            contains_str = sanitize_contains_str(req.params.get('contains-str', "").strip())
            
            # Get optional filter criteria
            must_include = sanitize_must_include(req.params.get('must-include', ''))
            
            # Get sort parameter
            sort_param = req.params.get('sort')
            if sort_param:
                sort_param = sort_param if sort_param in ["date", "name", "version", "id_asc", "id_desc"] else "default"
            
            # Get pagination parameters
            try:
                page = int(req.params.get('page', 1))
                page_size = int(req.params.get('page-size', 10))
                if page < 1:
                    return create_error_response(400, "Invalid pagination parameters: page must be >=1.")
                if page_size < 1 or page_size > 100:
                    return create_error_response(400, "Invalid pagination parameters: page-size must be between 1 and 100.")
            except ValueError:
                return create_error_response(400, "Invalid pagination parameters")

            # Create query object similar to the one used in the Data API
            query_object = {
                "query": contains_str,
                "sort": sort_param if sort_param else "default"
            }
            
            # Parse filter criteria similar to MongoDB implementation
            if must_include:
                try:
                    # Parse must-include parameter format: field1,value1,value2;field2,value1,value2
                    for group in must_include.split(';'):
                        if not group:
                            continue
                        parts = group.split(',')
                        if len(parts) < 2:
                            return create_error_response(400, "Invalid filter format")
                        
                        field = parts[0]
                        values = [sanitize_id(v) for v in parts[1:]]
                        if not all(values):
                            return create_error_response(400, "Invalid filter value format")
                        
                        # Add to query object similar to original implementation
                        query_object[field] = values
                except Exception as e:
                    logging.error(f"Error parsing filter criteria: {str(e)}")
                    return create_error_response(400, "Invalid filter format")

            # Build the aggregation pipeline
            pipeline = []
            
            # Add search query stage if a query is provided
            if contains_str:
                pipeline.extend(get_search_pipeline(query_object))
            
            # Add filter pipeline stages
            pipeline.extend(get_filter_pipeline(query_object))
            
            # Add latest version pipeline
            pipeline.extend(get_latest_version_pipeline())
            
            # Add sort pipeline
            pipeline.extend(get_sort_pipeline(query_object))
            
            # Add pagination
            pipeline.extend(get_page_pipeline(page, page_size))
            
            # Execute the aggregation
            results = list(collection.aggregate(pipeline))
            
            # Process results to match expected output format
            processed_results = []
            total_count = 0
            
            if results:
                processed_results = results
                total_count = results[0].get('totalCount', 0) if results else 0
                
                # Remove MongoDB _id field and ensure database field is added
                for resource in processed_results:
                    if '_id' in resource:
                        del resource['_id']
                    resource['database'] = "gem5-vision"  # Add database field like in original implementation
            
            response_data = {
                "documents": processed_results,
                "totalCount": total_count
            }
            
            return func.HttpResponse(
                body=json.dumps(response_data, default=json_util.default),
                headers={"Content-Type": "application/json"},
                status_code=200
            )

        except Exception as e:
            logging.error(f"Error searching resources: {str(e)}")
            return create_error_response(500, "Internal server error")


def get_sort(sort):
    """Return sort object based on sort parameter."""
    switch_dict = {
        "date": {"date": -1},
        "name": {"id": 1},
        "version": {"ver_latest": -1},
        "id_asc": {"id": 1},
        "id_desc": {"id": -1}
    }
    return switch_dict.get(sort, {"score": -1})

def get_latest_version_pipeline():
    """Return pipeline to get latest version of each resource."""
    return [
        {
            "$addFields": {
                "resource_version_parts": {
                    "$map": {
                        "input": {
                            "$split": ["$resource_version", "."],
                        },
                        "as": "item",
                        "in": {"$toInt": "$$item"},
                    },
                },
            },
        },
        {
            "$sort": {
                "id": 1,
                "resource_version_parts.0": -1,
                "resource_version_parts.1": -1,
                "resource_version_parts.2": -1,
                "resource_version_parts.3": -1,
            },
        },
        {
            "$group": {
                "_id": "$id",
                "latest_version": {
                    "$first": "$resource_version",
                },
                "document": {"$first": "$$ROOT"},
            },
        },
        {
            "$replaceRoot": {
                "newRoot": {
                    "$mergeObjects": [
                        "$document",
                        {
                            "id": "$_id",
                            "latest_version": "$latest_version",
                        },
                    ],
                },
            },
        },
    ]

def get_search_pipeline(query_object):
    """Return pipeline for text search."""
    
    pipeline = [
        {
            "$search": {
                "compound": {
                    "should": [
                        {
                            "text": {
                                "path": "id",
                                "query": query_object["query"],
                                "score": {
                                    "boost": {
                                        "value": 10
                                    }
                                }
                            }
                        },
                        {
                            "text": {
                                "path": "gem5_versions",
                                "query": "24.1",
                                "score": {
                                    "boost": {
                                        "value": 10
                                    }
                                }
                            }
                        }
                    ],
                    "must": [
                        {
                            "text": {
                                "query": query_object["query"],
                                "path": [
                                    "id",
                                    "description",
                                    "category",
                                    "architecture",
                                    "tags"
                                ],
                                "fuzzy": {
                                    "maxEdits": 2,
                                    "maxExpansions": 100
                                }
                            }
                        }
                    ]
                }
            }
        },
        {
            "$addFields": {
                "score": {
                    "$meta": "searchScore"
                }
            }
        }
    ]

    return pipeline

def get_filter_pipeline(query_object):
    """Return pipeline to apply filters."""
    pipeline = []
    
    # Filter by tags
    if query_object.get("tags"):
        pipeline.extend([
            {
                "$addFields": {
                    "tag": "$tags",
                },
            },
            {
                "$unwind": "$tag",
            },
            {
                "$match": {
                    "tag": {
                        "$in": query_object["tags"],
                    },
                },
            },
            {
                "$group": {
                    "_id": "$_id",
                    "doc": {
                        "$first": "$$ROOT",
                    },
                },
            },
            {
                "$replaceRoot": {
                    "newRoot": "$doc",
                },
            },
        ])
    
    # Filter by gem5_versions
    if query_object.get("gem5_versions"):
        pipeline.extend([
            {
                "$addFields": {
                    "version": "$gem5_versions",
                },
            },
            {
                "$unwind": "$version",
            },
            {
                "$match": {
                    "version": {
                        "$in": query_object["gem5_versions"],
                    },
                },
            },
            {
                "$group": {
                    "_id": "$_id",
                    "doc": {
                        "$first": "$$ROOT",
                    },
                },
            },
            {
                "$replaceRoot": {
                    "newRoot": "$doc",
                },
            },
        ])
    
    # Add other filters (category and architecture)
    match_conditions = []
    if query_object.get("category"):
        match_conditions.append({"category": {"$in": query_object["category"]}})
    
    if query_object.get("architecture"):
        match_conditions.append({"architecture": {"$in": query_object["architecture"]}})
    
    if match_conditions:
        pipeline.append({
            "$match": {
                "$and": match_conditions
            }
        })
    
    return pipeline

def get_sort_pipeline(query_object):
    """Return pipeline to apply sorting."""
    return [
        {
            "$addFields": {
                "ver_latest": {
                    "$max": {"$ifNull": ["$gem5_versions", []]},
                },
            },
        },
        {
            "$sort": get_sort(query_object.get("sort")),
        }
    ]

def get_page_pipeline(current_page, page_size):
    """Return pipeline to apply pagination."""
    return [
        {
            "$group": {
                "_id": None,
                "totalCount": {"$sum": 1},
                "items": {"$push": "$$ROOT"}
            }
        },
        {
            "$unwind": "$items"
        },
        {
            "$replaceRoot": {"newRoot": {
                "$mergeObjects": ["$items", {"totalCount": "$totalCount"}]
            }}
        },
        {
            "$skip": (current_page - 1) * page_size,
        },
        {
            "$limit": page_size,
        }
    ]