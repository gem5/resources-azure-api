# gem5 Resources API

## Overview

The gem5 Resources API is a comprehensive Azure Functions-based service that provides access to the gem5 resource database, which includes prebuilt disk images, kernel binaries, workloads, and microbenchmarks commonly used with the gem5 simulator.

The API integrates with MongoDB to deliver:

- **Resource Discovery**: Find resources by ID with version control
- **Batch Operations**: Retrieve multiple resources efficiently
- **Advanced Search**: Full-text search with filtering and pagination
- **Dependency Analysis**: Find workloads that depend on specific resources
- **Filter Management**: Dynamic filter options for enhanced resource discovery

## Architecture

### Technology Stack

- **Runtime**: Azure Functions (Python 3.8+)
- **Database**: MongoDB with Atlas Search
- **Authentication**: Anonymous access for all current endpoints (no API key required); support for secured endpoints can be added if needed in future deployments.
- **Caching**: Materialized views for filter data

### Database Collections

- **`resources`**: Main collection containing gem5 resources
- **`filter_values`**: Materialized view for cached filter options (updated daily via GitHub Actions)

## API Endpoints

### 1. Batch Resource Retrieval

**Endpoint**: `GET /api/resources/find-resources-in-batch`

Retrieve multiple resources in a single request with version control support.

**Parameters**:

- `id` (required, multiple): Resource identifiers (up to 40)
- `resource_version` (required, multiple): Corresponding versions or "None" for all versions

**Examples**:

```bash
# Get specific versions of multiple resources
GET /api/resources/find-resources-in-batch?id=riscv-ubuntu-20.04-boot&resource_version=3.0.0&id=arm-hello64-static&resource_version=1.0.0

# Mixed version requests (specific + all versions)
GET /api/resources/find-resources-in-batch?id=riscv-ubuntu-20.04-boot&resource_version=3.0.0&id=arm-hello64-static&resource_version=None
```

**Notes**:

- Each `id` parameter must have a corresponding `resource_version` parameter
- Use `resource_version=None` to retrieve all versions of a resource
- Returns a list of resources that were found even if not all requested resources were found.
- Returns an empty list is no resources were found.

### 2. Advanced Resource Search

**Endpoint**: `GET /api/resources/search`

Powerful search functionality with MongoDB Atlas Search integration, filtering, and pagination.

**Parameters**:

- `contains-str` (optional): Search term (searches across id, description, category, architecture, tags)
- `must-include` (optional): Filter criteria in format `field,value1,value2;field2,value1`. The `must-include` param expects semicolon-separated `field,value` groups. Each field may include multiple comma-separated values. Multiple fields are ANDed, multiple values within a field are ORed.
- `sort` (optional): Sort order (`date`, `name`, `version`, `id_asc`, `id_desc`, default: relevance score)
- `page` (optional): Page number (default: 1)
- `page-size` (optional): Results per page (1-100, default: 10)

**Supported Filter Fields**:

- `category`: Resource category (workload, binary, etc.)
- `architecture`: System architecture (ARM, RISCV, x86, etc.)
- `gem5_versions`: Compatible gem5 versions
- `tags`: Resource tags

**Examples**:

```bash
# Basic search
GET /api/resources/search?contains-str=ubuntu

# Search with single filter
GET /api/resources/search?contains-str=boot&must-include=architecture,x86

# Multiple filters with pagination
GET /api/resources/search?contains-str=ubuntu&must-include=category,workload;architecture,RISCV&page=1&page-size=20

# Sorted results
GET /api/resources/search?contains-str=hello&sort=date
```

**Response Format**:

```json
{
  "documents": [
    {
      "id": "resource-id",
      "resource_version": "1.0.0",
      "score": 12.5,
      "latest_version": "1.2.0",
      "database": "gem5-vision",
      // ... other resource fields
    }
  ],
  "totalCount": 150
}
```

### 3. Get Filter Options

**Endpoint**: `GET /api/resources/filters`

Retrieve available filter options for search functionality. Uses cached data from materialized views updated daily.

**Response Format**:

```json
{
  "category": ["binary", "workload", "kernel", "disk-image"],
  "architecture": ["ARM", "RISCV", "x86"],
  "gem5_versions": ["24.0", "23.1", "23.0", "22.1", "22.0"]
}
```

**Notes**:

- Categories and architectures are sorted alphabetically
- gem5_versions are sorted in descending order (newest first)
- Includes fallback to real-time aggregation if cached data unavailable

### 4. Get Dependent Workloads

**Endpoint**: `GET /api/resources/get-dependent-workloads`

Find workloads that depend on a specified resource ID.

**Parameters**:

- `id` (required): The resource ID to find dependencies for

**Example**:

```bash
GET /api/resources/get-dependent-workloads?id=x86-ubuntu-18.04-img
```

**Response Format**:

```json
[
  {
    "_id": "boot-exit-workload"
  },
  {
    "_id": "spec-2017-workload"
  }
]
```

### 5. List All Resources by gem5 Version

**Endpoint**: `GET /api/resources/list-all-resources`

Retrieve all resources that are compatible with a specific gem5 version. The endpoint performs prefix matching, so a version like `25.0.0.1` will match resources that have `25.0` or `25.0.0` in their `gem5_versions` field.

**Parameters**:

- `gem5-version` (required): The gem5 version to match against (e.g., "23.0", "25.0.0.1")
- `latest-version` (optional): If set to `"true"`, returns only the latest compatible version of each resource instead of all compatible versions. Default is `"false"` (returns all versions).

**Examples**:

```bash
# Get all resources compatible with gem5 version 23.0
GET /api/resources/list-all-resources?gem5-version=23.0

# Get all resources compatible with gem5 version 25.0.0.1
# This will match resources with gem5_versions containing "25", "25.0", "25.0.0", or "25.0.0.1"
GET /api/resources/list-all-resources?gem5-version=25.0.0.1

# Get only the latest version of each resource compatible with gem5 version 23.0
GET /api/resources/list-all-resources?gem5-version=23.0&latest-version=true
```

**Response Format**:

```json
[
  {
    "id": "riscv-ubuntu-20.04-boot",
    "resource_version": "3.0.0",
    "category": "workload",
    "architecture": "RISCV",
    "gem5_versions": ["23.0", "22.1", "22.0"],
    // ... other resource fields
  },
  {
    "id": "arm-hello64-static",
    "resource_version": "1.0.0",
    "category": "binary",
    "architecture": "ARM",
    "gem5_versions": ["23.0", "22.0"],
    // ... other resource fields
  }
]
```

**Notes**:

- Uses prefix matching: a parameter like `25.0.0.1` matches resources with `25.0`, `25.0.0`, or `25.0.0.1` in their `gem5_versions` field
- Version parameter must have at least `major` version (e.g., `23.0`), gem5 major versions follow the format `release-year.release_num` (eg, "25.1" would be the second release of year 2025).
- Returns all versions of resources that match
- Returns an empty list if no resources match the specified gem5 version

## Development Setup

### Prerequisites

- **Python**: 3.8+ (Azure Functions does not support Python 3.13)
- **Node.js**: Required for Azure Functions Core Tools
- **MongoDB**: Access to gem5 resources database
- **Azure Functions Core Tools**: v4.x

### Environment Setup

1. **Create Virtual Environment**:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. **Install Dependencies**:

```bash
pip install -r requirements.txt
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

3. **Configuration**:

Create `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "MONGO_CONNECTION_STRING": "mongodb+srv://user:pass@cluster.mongodb.net/gem5-resources?retryWrites=true&w=majority",
    "FUNCTIONS_WORKER_RUNTIME": "python"
  }
}
```

**Required Environment Variables**:

- `MONGO_CONNECTION_STRING`: MongoDB Atlas connection string
- `API_BASE_URL`: Base URL for testing (optional, defaults to `http://localhost:7071/api`)

### Project Structure

```python
gem5-resources-api/
├── function_app.py              # Main app initialization
├── functions/                   # Individual function modules. Each file inside functions/ registers its route via a shared FunctionApp instance.
│   ├── get_resources_by_batch.py
│   ├── search_resources.py
│   ├── get_filters.py
│   ├── get_dependent_workloads.py
│   └── list_all_resources.py
├── shared/                      # Shared utilities
│   ├── database.py             # Database connection & config
│   └── utils.py                # Common utilities & validation
├── tests/                      # Test suite
│   └── resources_api_tests.py
├── requirements.txt
└── local.settings.json
```

## Running the Application

### Local Development

Start the Azure Function locally. By default, the development server starts at `http://localhost:7071`. Use func start `--port <port>` to run on a different port:

```bash
func start
```

Expected output:

```bash
Functions:
    get_resources_by_batch: [GET] http://localhost:7071/api/resources/find-resources-in-batch
    search_resources: [GET] http://localhost:7071/api/resources/search
    get_filters: [GET] http://localhost:7071/api/resources/filters
    get_dependent_workloads: [GET] http://localhost:7071/api/resources/get-dependent-workloads
    list_all_resources: [GET] http://localhost:7071/api/resources/list-all-resources
```

### Testing

Execute the comprehensive test suite. The test suite assumes access to the gem5 resources database:

```bash
# Set API base URL (optional)
export API_BASE_URL=http://localhost:7071/api

# Run all tests with verbose output
python -m unittest tests.resources_api_tests -v

# Run specific test categories
python -m unittest tests.resources_api_tests.TestResourcesAPIIntegration.test_search_basic_contains_str -v
```

### Test Coverage

The test suite validates:

**Core Functionality**:

- Resource retrieval by ID (single & batch)
- Version-specific queries
- Search with filtering and pagination
- Filter option retrieval
- Dependency analysis

**Error Handling**:

- Invalid parameters
- Missing resources
- Malformed requests
- Database connection issues

**Edge Cases**:

- Special characters in search
- Large batch requests
- Pagination boundaries
- Case-insensitive search

## Error Handling

### HTTP Status Codes

- **200 OK**: Successful request
- **400 Bad Request**: Invalid parameters or malformed request
- **404 Not Found**: Resource(s) not found
- **500 Internal Server Error**: Database or server error

### Error Response Format

```json
{
  "error": "Descriptive error message explaining the issue"
}
```

### Common Error Scenarios

- **Invalid Resource ID**: Non-alphanumeric characters (except dash, underscore, dot)
- **Version Format**: Invalid semantic version format
- **Batch Mismatch**: Unequal number of IDs and versions
- **Search Filters**: Malformed filter syntax
- **Pagination**: Invalid page or page-size values

## Deployment

This repository has github actions set up that will re deploy the functions once a commit is pushed to the repository.

## Contributing

### Adding New Endpoints

Each new endpoint file must be manually imported and registered in function_app.py using the pattern shown below.

1. **Create Function Module**:

   ```python
   # functions/new_endpoint.py
   def register_function(app, collection):
       @app.route(route="resources/new-endpoint", auth_level=func.AuthLevel.ANONYMOUS)
       def new_endpoint(req: func.HttpRequest) -> func.HttpResponse:
           # Implementation
   ```

2. **Register in Main App**:

   ```python
   # function_app.py
   from functions import new_endpoint
   new_endpoint.register_function(app, collection)
   ```

3. **Add Tests**:

   ```python
   # tests/resources_api_tests.py
   def test_new_endpoint(self):
       # Test implementation
   ```

## gem5 Integration

### Usage in gem5 Website

The API serves the gem5 resources website (resources.gem5.org) by providing:

- Resource details
- Search functionality
- Filter options for resource discovery
- Dependency information for workloads

### Usage in gem5 Simulator

The gem5 simulator integrates with this API to:

- Download resources dynamically
- Validate resource compatibility

### Community Impact

This API enables the gem5 community to:

- Share resources efficiently
- Discover relevant resources for research
- Maintain compatibility across gem5 versions
- Track resource dependencies and usage

## Support and Maintenance

### Regular Maintenance Tasks

- Update filter values materialized view (automated via GitHub Actions)

### Getting Help

- **Issues**: Report bugs or feature requests via GitHub issues
- **Documentation**: Refer to this README and inline code documentation
- **Community**: Engage with gem5 community forums and mailing lists

For technical questions about the API implementation, consult the test suite for expected behavior and error handling patterns.
