#!/usr/bin/env python3
# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import json
import re

import azure.functions as func
from bson import json_util


def create_error_response(status_code: int, message: str) -> func.HttpResponse:
    """Create an error response with appropriate headers."""
    return func.HttpResponse(
        body=json.dumps({"error": message}),
        status_code=status_code,
        headers={"Content-Type": "application/json"},
    )


def sanitize_id(value):
    # Only allow alphanumeric, dash, underscore, and dot, max 100 chars
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.match(r"^[\w\-\.]{1,100}$", value):
        return None
    return value


def sanitize_version(value):
    # Only allow digits and dots, max 20 chars
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.match(r"^[0-9\.]{1,20}$", value):
        return None
    return value


def sanitize_contains_str(value):
    # Allow basic printable chars, max 200 chars
    if not isinstance(value, str):
        return ""
    value = value.strip()
    value = re.sub(r"[^\w\s\-\.,:;!?@#%&()\[\]{}<>/\\=+*\'\"]", "", value)
    return value[:200]


def sanitize_must_include(value):
    # Only allow field,value1,value2;field2,value1,value2, max 500 chars
    # Allow dots for version numbers like "24.1"
    if not isinstance(value, str):
        return ""
    value = value.strip()
    value = re.sub(r"[^\w,;\-\.]", "", value)
    return value[:500]


def create_json_response(data, status_code=200):
    """Create a JSON response with the given data."""
    return func.HttpResponse(
        body=json.dumps(data, default=json_util.default),
        headers={"Content-Type": "application/json"},
        status_code=status_code,
    )
