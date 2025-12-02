# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import json
import logging

import azure.functions as func

from shared.utils import (
    create_error_response,
    sanitize_contains_str,
    sanitize_id,
    sanitize_must_include,
)


def register_function(app, search_client):
    """Register the function with the app."""

    @app.function_name(name="search_resources")
    @app.route(route="resources/search", auth_level=func.AuthLevel.ANONYMOUS)
    def search_resources(req: func.HttpRequest) -> func.HttpResponse:
        """
        Search resources with filtering capabilities using Azure AI Search.

        Route: /resources/search

        Query Parameters:
        - contains-str: Optional. The search term to find resources.
        - must-include: Optional. A CSV-formatted string defining filter criteria.
        - sort: Optional. Sort criteria ('date', 'name', 'version', 'id_asc', 'id_desc'). Default is score-based.
        - page: Optional. Page number for pagination (default: 1).
        - page-size: Optional. Number of results per page (default: 10).
        """
        logging.info("Processing request to search resources")
        try:
            # Get search query
            contains_str = sanitize_contains_str(
                req.params.get("contains-str", "").strip()
            )

            # Get optional filter criteria
            must_include = sanitize_must_include(
                req.params.get("must-include", "")
            )

            # Get sort parameter
            sort_param = req.params.get("sort")
            if sort_param:
                sort_param = (
                    sort_param
                    if sort_param
                    in ["date", "name", "version", "id_asc", "id_desc"]
                    else "default"
                )

            # Get pagination parameters
            try:
                page = int(req.params.get("page", 1))
                page_size = int(req.params.get("page-size", 10))
                if page < 1:
                    return create_error_response(
                        400, "Invalid pagination parameters: page must be >=1."
                    )
                if page_size < 1 or page_size > 100:
                    return create_error_response(
                        400,
                        "Invalid pagination parameters: page-size must be between 1 and 100.",
                    )
            except ValueError:
                return create_error_response(
                    400, "Invalid pagination parameters"
                )

            query_object = {
                "query": contains_str,
                "sort": sort_param if sort_param else "default",
            }

            if must_include:
                try:
                    # Parse must-include parameter format: field1,value1,value2;field2,value1,value2
                    for group in must_include.split(";"):
                        if not group:
                            continue
                        parts = group.split(",")
                        if len(parts) < 2:
                            return create_error_response(
                                400, "Invalid filter format"
                            )

                        field = parts[0]
                        values = [sanitize_id(v) for v in parts[1:]]
                        if not all(values):
                            return create_error_response(
                                400, "Invalid filter value format"
                            )

                        query_object[field] = values
                except Exception as e:
                    logging.error(f"Error parsing filter criteria: {str(e)}")
                    return create_error_response(400, "Invalid filter format")

            odata_filter = build_odata_filter(query_object)

            # Build search text with Lucene query syntax
            # Mimics MongoDB Atlas Search behavior:
            # - Text search across id, description, category, architecture, tags
            # - Boost matches on id field
            # - Word order doesn't matter (each term searched independently)
            if contains_str:
                # Split into terms - Atlas Search tokenizes and matches each term
                terms = contains_str.split()

                # Build query that requires all terms (like Atlas "must" clause)
                # but allows them in any order and any field
                term_clauses = []
                for term in terms:
                    escaped_term = escape_lucene_query(term)
                    # Search each term across all searchable fields
                    # Use quoted phrase for exact matching, plus unquoted for partial
                    # Boost id matches by 10x (like Atlas Search boost)
                    term_clauses.append(
                        f'(id:"{escaped_term}"^10 OR id:{escaped_term}*^10 OR '
                        f'description:"{escaped_term}" OR description:{escaped_term}* OR '
                        f'category:"{escaped_term}" OR category:{escaped_term}* OR '
                        f'architecture:"{escaped_term}" OR architecture:{escaped_term}* OR '
                        f'tags:"{escaped_term}" OR tags:{escaped_term}* OR '
                        f'"{escaped_term}" OR {escaped_term}*)'
                    )

                # Join with AND - all terms must match (like Atlas "must" clause)
                search_text = " AND ".join(term_clauses)
                query_type = "full"  # Lucene query syntax
            else:
                search_text = "*"
                query_type = "simple"

            # Fetch ALL results from Azure AI Search (no server-side pagination)
            # We need all results to deduplicate by id and keep only latest version
            all_results = []

            results = search_client.search(
                search_text=search_text,
                filter=odata_filter,
                include_total_count=True,
                top=1000,  # Max allowed by Azure AI Search
                query_type=query_type,
            )

            for result in results:
                # Convert to dict and add score
                doc = dict(result)
                doc["score"] = result.get("@search.score", 0)
                all_results.append(doc)

            logging.info(f"Raw results count: {len(all_results)}")

            unique_resources = keep_latest_versions(all_results)

            # Apply sorting
            sorted_resources = apply_sorting(
                unique_resources, query_object.get("sort", "default")
            )

            # Calculate total count before pagination
            total_count = len(sorted_resources)

            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_results = sorted_resources[start_idx:end_idx]

            # Clean up results for response
            for resource in paginated_results:
                # Remove Azure Search internal fields
                keys_to_remove = [
                    "@search.score",
                    "@search.highlights",
                    "@search.reranker_score",
                ]
                for key in keys_to_remove:
                    resource.pop(key, None)
                resource["database"] = "gem5-vision"

            response_data = {
                "documents": paginated_results,
                "totalCount": total_count,
            }

            return func.HttpResponse(
                body=json.dumps(response_data),
                headers={"Content-Type": "application/json"},
                status_code=200,
            )

        except Exception as e:
            logging.error(f"Error searching resources: {str(e)}")
            return create_error_response(500, "Internal server error")


def escape_lucene_query(query_str):
    """
    Escape special characters in a Lucene query string.
    https://learn.microsoft.com/en-us/azure/search/query-lucene-syntax#escaping-special-characters

    Lucene special characters: + - && || ! ( ) { } [ ] ^ " ~ * ? : \\ /

    Parameters:
    - query_str (str): The raw query string.

    Returns:
    - str: The escaped query string safe for Lucene syntax.
    """
    # Characters that need escaping in Lucene (except quotes which are used for phrases)
    special_chars = [
        "\\",
        "+",
        "-",
        "&",
        "|",
        "!",
        "(",
        ")",
        "{",
        "}",
        "[",
        "]",
        "^",
        "~",
        "*",
        "?",
        ":",
        "/",
    ]

    escaped = query_str
    for char in special_chars:
        escaped = escaped.replace(char, f"\\{char}")

    escaped = escaped.replace('"', '\\"')

    return escaped


def build_odata_filter(query_object):
    """
    Build an OData filter string for Azure AI Search based on query parameters.

    Parameters:
    - query_object (dict): Dictionary containing filter keys and values.

    Returns:
    - str or None: OData filter string, or None if no filters.
    """
    filters = []

    # Filter by category
    if query_object.get("category"):
        values = query_object["category"]
        if len(values) == 1:
            filters.append(f"category eq '{values[0]}'")
        else:
            category_filters = " or ".join(
                [f"category eq '{v}'" for v in values]
            )
            filters.append(f"({category_filters})")

    # Filter by architecture
    if query_object.get("architecture"):
        values = query_object["architecture"]
        if len(values) == 1:
            filters.append(f"architecture eq '{values[0]}'")
        else:
            arch_filters = " or ".join(
                [f"architecture eq '{v}'" for v in values]
            )
            filters.append(f"({arch_filters})")

    # Filter by tags (collection field)
    if query_object.get("tags"):
        values = query_object["tags"]
        tag_filters = " or ".join([f"tags/any(t: t eq '{v}')" for v in values])
        filters.append(f"({tag_filters})")

    # Filter by gem5_versions (collection field)
    if query_object.get("gem5_versions"):
        values = query_object["gem5_versions"]
        version_filters = " or ".join(
            [f"gem5_versions/any(v: v eq '{v}')" for v in values]
        )
        filters.append(f"({version_filters})")

    if filters:
        return " and ".join(filters)
    return None


def parse_version(version_str):
    """
    Parse a semantic version string (x.y.z) into a tuple of integers for comparison.

    Parameters:
    - version_str (str): Version string like "1.2.3"

    Returns:
    - tuple: Tuple of integers (major, minor, patch) or (0, 0, 0) if parsing fails.
    """
    try:
        parts = version_str.split(".")
        return tuple(int(p) for p in parts)
    except (ValueError, AttributeError):
        return (0, 0, 0)


def keep_latest_versions(results):
    """
    Deduplicate results by resource id, keeping only the document with
    the highest semantic version. Also preserves the maximum search score
    across all versions for proper relevance sorting.

    Parameters:
    - results (list): List of search result documents.

    Returns:
    - list: List of unique resources with only the latest version.
    """
    latest_by_id = {}
    max_score_by_id = {}

    for doc in results:
        resource_id = doc.get("id")
        if not resource_id:
            continue

        current_version = parse_version(doc.get("resource_version", "0.0.0"))
        current_score = doc.get("score", 0)

        if resource_id not in max_score_by_id:
            max_score_by_id[resource_id] = current_score
        else:
            max_score_by_id[resource_id] = max(
                max_score_by_id[resource_id], current_score
            )

        if resource_id not in latest_by_id:
            latest_by_id[resource_id] = doc
        else:
            existing_version = parse_version(
                latest_by_id[resource_id].get("resource_version", "0.0.0")
            )
            if current_version > existing_version:
                latest_by_id[resource_id] = doc

    for resource_id, doc in latest_by_id.items():
        doc["score"] = max_score_by_id.get(resource_id, 0)

    return list(latest_by_id.values())


def apply_sorting(results, sort_param):
    """
    Sort results based on the sort parameter.

    Parameters:
    - results (list): List of documents to sort.
    - sort_param (str): Sort parameter ('date', 'name', 'version', 'id_asc', 'id_desc', or 'default').

    Returns:
    - list: Sorted list of documents.
    """
    if sort_param == "date":
        return sorted(results, key=lambda x: x.get("date", ""), reverse=True)
    elif sort_param == "name" or sort_param == "id_asc":
        return sorted(results, key=lambda x: x.get("id", "").lower())
    elif sort_param == "id_desc":
        return sorted(
            results, key=lambda x: x.get("id", "").lower(), reverse=True
        )
    elif sort_param == "version":
        return sorted(
            results,
            key=lambda x: max(x.get("gem5_versions", ["0"]), default="0"),
            reverse=True,
        )
    else:
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
