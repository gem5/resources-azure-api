# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


def get_search_client():
    """
    Creates and returns an Azure AI Search client.

    Required environment variables:
    - AZURE_SEARCH_ENDPOINT: The Azure AI Search service endpoint
    - AZURE_SEARCH_API_KEY: The API key for authentication
    - AZURE_SEARCH_INDEX_NAME: The name of the search index

    Returns:
        SearchClient: An Azure AI Search client instance
    """
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    api_key = os.environ.get("AZURE_SEARCH_API_KEY")
    index_name = os.environ.get("AZURE_SEARCH_INDEX_NAME")

    if not all([endpoint, api_key, index_name]):
        logging.error("Missing Azure Search configuration")
        raise ValueError(
            "Missing required environment variables: "
            "AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, or AZURE_SEARCH_INDEX_NAME"
        )

    credential = AzureKeyCredential(api_key)
    client = SearchClient(
        endpoint=endpoint, index_name=index_name, credential=credential
    )

    return client
