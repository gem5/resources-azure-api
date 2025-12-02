# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause


import azure.functions as func

from functions import (
    get_dependent_workloads,
    get_filters,
    get_resources_by_batch,
    search_resources,
)
from shared.azure_search_client import get_search_client
from shared.database import initialize_database

# Initialize the function app
app = func.FunctionApp()

# Initialize database connection
db, collection = initialize_database()

# Initialize Azure Search client
search_client = get_search_client()

# Register functions
get_resources_by_batch.register_function(app, collection)
search_resources.register_function(app, search_client)
get_filters.register_function(app, collection, db["filter_values"])
get_dependent_workloads.register_function(app, collection)
