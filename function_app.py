import azure.functions as func
import logging
from shared.database import initialize_database
from functions import (
    get_resource_by_id,
    get_resources_by_batch,
    search_resources,
    get_filters,
    get_dependent_workloads
)

# Initialize the function app
app = func.FunctionApp()

# Initialize database connection
db, collection = initialize_database()

# Register functions
get_resource_by_id.register_function(app, collection)
get_resources_by_batch.register_function(app, collection)
search_resources.register_function(app, collection)
get_filters.register_function(app, collection, db["filter_values"])
get_dependent_workloads.register_function(app, collection)