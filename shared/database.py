# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import os
import pymongo
import logging

# Define explicit allow-list for resource fields
# Comes from the schema
# https://github.com/gem5/gem5-resources-website/blob/stable/public/gem5-resources-schema.json
RESOURCE_FIELDS = {
    "id": 1,
    "resource_version": 1,
    "category": 1,
    "author": 1,
    "code_examples": 1,
    "description": 1,
    "source_url": 1,
    "license": 1,
    "tags": 1,
    "example_usage": 1,
    "gem5_versions": 1,
    "size": 1,
    "url": 1,
    "is_tar_archive": 1,
    "md5sum": 1,
    "is_zipped": 1,
    "architecture": 1,
    "root_partition": 1,  # disk-image
    "resource_directory": 1,  # workload
    "arguments": 1,  # abstract-binary
    "region_id": 1,  # looppoint-json
    "simpoint_interval": 1,  # abstract-simpoint
    "simpoint_list": 1,  # abstract-simpoint
    "weight_list": 1,  # abstract-simpoint
    "warmup_interval": 1,  # abstract-simpoint
    "workload_name": 1,  # abstract-simpoint
    "function": 1,  # abstract-workload
    "additional_params": 1,  # abstract-workload
    "resources": 1,  # abstract-workload
    "source": 1,  # abstract-file
    "documentation": 1,  # abstract-file
    "workloads": 1,  # suite
    "input-group": 1,  # suite workloads
    "_id": 0
}

def initialize_database():
    """Initialize MongoDB connection."""
    try:
        # Load MongoDB connection string from environment variables
        MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017")
        
        # Connect to MongoDB
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        db = client["gem5-vision"]
        collection = db["resources"]
        
        return db, collection
    except Exception as e:
        logging.error(f"Error initializing database: {str(e)}")
        raise