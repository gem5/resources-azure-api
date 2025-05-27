# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2025 The Regents of the University of California

#!/usr/bin/env python3
"""
Script to update the filter values collection.
This script runs as a GitHub Action to periodically update the materialized view
of filter values from the resources collection.
"""

import os
import logging
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables (for local testing)
load_dotenv()

def main():
    """Main function to update the filter values collection."""
    try:
        # Get MongoDB connection details from environment variables
        connection_string = os.environ.get('MONGODB_CONNECTION_STRING')
        database_name = os.environ.get('MONGODB_DATABASE_NAME')
        
        if not connection_string or not database_name:
            raise ValueError("Missing required environment variables for MongoDB connection")
        
        # Connect to MongoDB
        client = MongoClient(connection_string)
        db = client[database_name]
        
        # Collection references
        resources_collection = db.resources
        filter_values_collection = db.filter_values
        
        logger.info("Connected to MongoDB. Starting filter values update.")
        
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
        results = list(resources_collection.aggregate(pipeline))
        
        # If no results, create empty arrays
        if not results:
            filters = {
                "category": [],
                "architecture": [],
                "gem5_versions": []
            }
        else:
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
        
        # Update the filter_values collection
        # filter_values_collection.delete_many({})  # Clear existing entries
        filter_values_collection.insert_one({
            "_id": "current",
            "timestamp": datetime.now(),
            "filters": filters
        })
        
        logger.info("Filter values collection successfully updated.")
        
    except Exception as e:
        logger.error(f"Error updating filter values: {str(e)}")
        raise
    finally:
        # Close the MongoDB connection
        if 'client' in locals():
            client.close()
            logger.info("MongoDB connection closed.")

if __name__ == "__main__":
    main()