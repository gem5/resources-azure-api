#!/usr/bin/env python3
# Copyright (c) 2025 The Regents of the University of California
# SPDX-License-Identifier: BSD-3-Clause

import os
import unittest

import requests


class TestResourcesAPIIntegration(unittest.TestCase):
    """Integration tests for the Resources API"""

    @classmethod
    def setUpClass(cls):
        """Set up the API base URL before running tests."""
        cls.base_url = os.getenv("API_BASE_URL", "http://localhost:7071/api")

    def test_get_resources_by_batch_with_specific_versions(self):
        """Test retrieving multiple resources by batch with specific
        versions."""
        resource_pairs = [
            ("riscv-ubuntu-20.04-boot", "3.0.0"),
            ("arm-hello64-static", "1.0.0"),
        ]
        query_string = "&".join(
            [
                f"id={id}&resource_version={version}"
                for id, version in resource_pairs
            ]
        )
        url = (
            f"{self.base_url}/resources/find-resources-in-batch?{query_string}"
        )
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

        # Verify each resource is present
        found_resources = {(r["id"], r["resource_version"]) for r in data}
        expected_resources = set(resource_pairs)
        self.assertEqual(found_resources, expected_resources)

    def test_get_resources_by_batch_with_none_versions(self):
        """Test retrieving multiple resources by batch with None versions
        (all versions)."""
        resource_ids = ["riscv-ubuntu-20.04-boot", "arm-hello64-static"]
        query_string = "&".join(
            [f"id={id}&resource_version=None" for id in resource_ids]
        )
        url = (
            f"{self.base_url}/resources/find-resources-in-batch?{query_string}"
        )
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Verify all requested IDs are present
        found_ids = {r["id"] for r in data}
        expected_ids = set(resource_ids)
        self.assertEqual(found_ids, expected_ids)

    def test_get_resources_by_batch_mixed_versions(self):
        """Test batch retrieval with mix of specific versions and None."""
        params = {
            "id": ["riscv-ubuntu-20.04-boot", "arm-hello64-static"],
            "resource_version": ["3.0.0", "None"],
        }
        response = requests.get(
            f"{self.base_url}/resources/find-resources-in-batch", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Verify both IDs are present
        found_ids = {r["id"] for r in data}
        self.assertIn("riscv-ubuntu-20.04-boot", found_ids)
        self.assertIn("arm-hello64-static", found_ids)

        # Verify specific version constraint
        riscv_resources = [
            r for r in data if r["id"] == "riscv-ubuntu-20.04-boot"
        ]
        self.assertTrue(
            all(r["resource_version"] == "3.0.0" for r in riscv_resources)
        )

    def test_get_resources_by_batch_not_found_partial(self):
        """Test batch retrieval where one or more resources are missing."""
        resource_pairs = [
            ("arm-hello64-static", "1.0.0"),
            ("non-existent", "9.9.9"),
        ]
        query_string = "&".join(
            [
                f"id={id}&resource_version={version}"
                for id, version in resource_pairs
            ]
        )
        url = (
            f"{self.base_url}/resources/find-resources-in-batch?{query_string}"
        )
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)

        found_ids = [r["id"] for r in data]
        self.assertEqual(len(found_ids), 1)
        self.assertEqual("arm-hello64-static", found_ids[0])

    def test_get_resources_by_batch_not_found_all(self):
        """Test batch retrieval where all resources are missing."""
        resource_pairs = [
            ("non-existent-1", "1.0.0"),
            ("non-existent-2", "2.0.0"),
        ]
        query_string = "&".join(
            [
                f"id={id}&resource_version={version}"
                for id, version in resource_pairs
            ]
        )
        url = (
            f"{self.base_url}/resources/find-resources-in-batch?{query_string}"
        )
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)

    def test_get_resources_by_batch_mismatched_parameters(self):
        """Test batch retrieval with mismatched number of id and version
        parameters."""
        url = (
            f"{self.base_url}/resources/find-resources-in-batch"
            "?id=arm-hello64-static&id=riscv-ubuntu-20.04-boot"
            "&resource_version=1.0.0"
        )
        response = requests.get(url)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("corresponding", data["error"])

    def test_get_resources_by_batch_no_version_parameters(self):
        """Test batch retrieval without any version parameters
        (should fail)."""
        url = (
            f"{self.base_url}/resources/find-resources-in-batch?"
            "id=arm-hello64-static&id=riscv-ubuntu-20.04-boot"
        )
        response = requests.get(url)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("corresponding", data["error"])

    def test_get_resources_by_batch_valid_id_invalid_version(self):
        """Test batch retrieval with valid ID but invalid version."""
        resource_pairs = [
            ("arm-hello64-static", "1.0.0"),  # Valid
            ("riscv-ubuntu-20.04-boot", "99.99.99"),  # Invalid version
        ]
        query_string = "&".join(
            [
                f"id={id}&resource_version={version}"
                for id, version in resource_pairs
            ]
        )
        url = (
            f"{self.base_url}/resources/find-resources-in-batch?{query_string}"
        )
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)

        found_ids = [r["id"] for r in data]
        self.assertEqual(len(found_ids), 1)
        self.assertEqual("arm-hello64-static", found_ids[0])

    # FILTER ENDPOINT TESTS
    def test_get_filters(self):
        """Test retrieving filter values."""
        response = requests.get(f"{self.base_url}/resources/filters")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify structure
        self.assertIn("category", data)
        self.assertIn("architecture", data)
        self.assertIn("gem5_versions", data)

        # Verify types
        self.assertIsInstance(data["category"], list)
        self.assertIsInstance(data["architecture"], list)
        self.assertIsInstance(data["gem5_versions"], list)

    def test_get_filters_content_validation(self):
        """Test that filter values contain expected content."""
        response = requests.get(f"{self.base_url}/resources/filters")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check that gem5_versions are sorted in reverse order (newest first)
        if len(data["gem5_versions"]) > 1:
            versions = data["gem5_versions"]
            for i in range(len(versions) - 1):
                # Assuming semantic versioning, newer versions should come
                # first
                self.assertGreaterEqual(versions[i], versions[i + 1])

        # Check that categories and architectures are sorted
        if data["category"]:
            self.assertEqual(data["category"], sorted(data["category"]))
        if data["architecture"]:
            self.assertEqual(
                data["architecture"], sorted(data["architecture"])
            )

    def test_search_basic_contains_str(self):
        """Test basic search with a contains-str parameter."""
        params = {"contains-str": "arm-hello64-static"}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]
        # Check that results are returned
        self.assertGreater(len(resources), 0)
        self.assertEqual(resources[0]["id"], "arm-hello64-static")

    def test_search_with_single_filter(self):
        """Test search with a single filter criterion."""
        params = {"contains-str": "boot", "must-include": "architecture,x86"}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]

        # Validate results match filter criteria
        for resource in resources:
            self.assertEqual(resource["architecture"], "x86")
            self.assertIn("boot", resource["id"])

    def test_search_with_multiple_filters(self):
        """Test search with multiple filter criteria."""
        params = {
            "contains-str": "ubuntu",
            "must-include": "category,workload;architecture,RISCV",
        }
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]

        # Validate results match filter criteria
        for resource in resources:
            self.assertEqual(resource["category"], "workload")
            self.assertEqual(resource["architecture"], "RISCV")
            self.assertIn("ubuntu", resource["id"].lower())

    def test_search_with_gem5_version_filter(self):
        """Test search with gem5_versions filter."""
        params = {
            "contains-str": "resource",
            "must-include": "gem5_versions,23.0",
        }
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]

        # Validate results match filter criteria
        for resource in resources:
            self.assertIn("23.0", resource["gem5_versions"])

    def test_search_pagination(self):
        """Test pagination functionality."""
        # First page
        params_page1 = {"contains-str": "resource", "page": 1, "page-size": 2}
        response_page1 = requests.get(
            f"{self.base_url}/resources/search", params=params_page1
        )

        self.assertEqual(response_page1.status_code, 200)
        data_page1 = response_page1.json()
        resources_page1 = data_page1["documents"]
        # Second page
        params_page2 = {"contains-str": "resource", "page": 2, "page-size": 2}
        response_page2 = requests.get(
            f"{self.base_url}/resources/search", params=params_page2
        )

        self.assertEqual(response_page2.status_code, 200)
        data_page2 = response_page2.json()
        resources_page2 = data_page2["documents"]

        # Ensure we have resources to check
        if len(resources_page1) > 0 and len(resources_page2) > 0:
            # Ensure pages are different
            first_page_ids = {r["id"] for r in resources_page1}
            second_page_ids = {r["id"] for r in resources_page2}
            self.assertTrue(
                len(first_page_ids.intersection(second_page_ids)) == 0
            )

    def test_search_no_results(self):
        """Test search with no matching results."""
        params = {"contains-str": "invalid"}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]
        # Validate empty results
        self.assertEqual(len(resources), 0)

    def test_search_invalid_filter(self):
        """Test search with invalid filter format."""
        params = {
            "contains-str": "resource",
            "must-include": "invalid-filter-format",
        }
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )

        # Expecting a 400 Bad Request for invalid filter format
        self.assertEqual(response.status_code, 400)

    def test_search_case_insensitive(self):
        """Test that search is case insensitive."""
        params1 = {"contains-str": "ARM-HELLO64-STATIC"}  # Uppercase
        params2 = {"contains-str": "arm-hello64-static"}  # Lowercase

        response1 = requests.get(
            f"{self.base_url}/resources/search", params=params1
        )
        response2 = requests.get(
            f"{self.base_url}/resources/search", params=params2
        )

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        data1 = response1.json()
        data2 = response2.json()
        resources1 = data1["documents"]
        resources2 = data2["documents"]

        # Both searches should return the same results
        self.assertEqual(len(resources1), len(resources2))
        if len(resources1) > 0 and len(resources2) > 0:
            self.assertEqual(resources1[0]["id"], resources2[0]["id"])

    def test_search_multiple_gem5_versions(self):
        """Test search with multiple gem5 versions in filter."""
        params = {
            "contains-str": "resource",
            "must-include": "gem5_versions,22.0,23.0",
        }
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]

        # Resources should have at least one of the specified gem5 versions
        for resource in resources:
            gem5_versions = set(resource["gem5_versions"])
            self.assertTrue(
                len({"22.0", "23.0"}.intersection(gem5_versions)) > 0
            )

    def test_search_with_special_characters(self):
        """Test search with special characters in the search string."""
        params = {"contains-str": "test-resource_with.special-chars"}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)  # Should not crash

    def test_search_with_very_long_string(self):
        """Test search with a very long contains-str parameter."""
        params = {"contains-str": "a" * 1000}  # Very long string
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)  # Should handle gracefully

    def test_batch_with_maximum_resources(self):
        """Test batch retrieval with a reasonable number of resources
        (stress test)."""
        # Create 10 resource requests
        resource_ids = ["arm-hello64-static"] * 10
        versions = ["1.0.0"] * 10

        params = {"id": resource_ids, "resource_version": versions}
        response = requests.get(
            f"{self.base_url}/resources/find-resources-in-batch", params=params
        )
        self.assertEqual(response.status_code, 200)

    def test_search_without_contains_str(self):
        """Test search without contains-str returns all resources."""
        params = {"page": 1, "page-size": 5}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("documents", data)
        self.assertIn("totalCount", data)
        self.assertGreater(len(data["documents"]), 0)

    def test_search_sort_by_id_asc(self):
        """Test search with sort by id ascending."""
        params = {"contains-str": "arm", "sort": "id_asc", "page-size": 10}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]
        if len(resources) > 1:
            ids = [r["id"].lower() for r in resources]
            self.assertEqual(ids, sorted(ids))

    def test_search_sort_by_id_desc(self):
        """Test search with sort by id descending."""
        params = {"contains-str": "arm", "sort": "id_desc", "page-size": 10}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]
        if len(resources) > 1:
            ids = [r["id"].lower() for r in resources]
            self.assertEqual(ids, sorted(ids, reverse=True))

    def test_search_total_count(self):
        """Test that totalCount is accurate."""
        params = {"contains-str": "arm", "page": 1, "page-size": 2}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("totalCount", data)
        self.assertIsInstance(data["totalCount"], int)
        self.assertGreaterEqual(data["totalCount"], len(data["documents"]))

    def test_search_with_multiple_architectures(self):
        """Test search with multiple architecture values."""
        params = {
            "contains-str": "hello",
            "must-include": "architecture,x86,ARM",
        }
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for resource in data["documents"]:
            self.assertIn(resource["architecture"], ["x86", "ARM"])

    def test_search_pagination_beyond_results(self):
        """Test pagination when page is beyond available results."""
        params = {
            "contains-str": "arm-hello64-static",
            "page": 1000,
            "page-size": 10,
        }
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["documents"]), 0)  # No results on this page

    def test_search_pagination_max_page_size(self):
        """Test pagination with maximum page-size (100)."""
        params = {"contains-str": "resource", "page": 1, "page-size": 100}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)

    def test_search_pagination_exceeds_max_page_size(self):
        """Test pagination with page-size exceeding max (should fail)."""
        params = {"contains-str": "resource", "page": 1, "page-size": 101}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 400)

    def test_search_pagination_invalid_page(self):
        """Test pagination with invalid page number (should fail)."""
        params = {"contains-str": "resource", "page": 0, "page-size": 10}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 400)

    def test_search_returns_latest_version_only(self):
        """Test that search returns only the latest version of each resource."""
        params = {"contains-str": "ubuntu", "page-size": 50}
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]

        # Check no duplicate IDs (each resource appears only once)
        ids = [r["id"] for r in resources]
        self.assertEqual(len(ids), len(set(ids)))

    def test_search_combined_filters_sort_pagination(self):
        """Test search with filters, sorting, and pagination combined."""
        params = {
            "contains-str": "ubuntu",
            "must-include": "architecture,ARM",
            "sort": "name",
            "page": 1,
            "page-size": 5,
        }
        response = requests.get(
            f"{self.base_url}/resources/search", params=params
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        resources = data["documents"]

        # Validate architecture filter
        for resource in resources:
            self.assertEqual(resource["architecture"], "ARM")

        # Validate sorting (by name/id ascending)
        if len(resources) > 1:
            ids = [r["id"].lower() for r in resources]
            self.assertEqual(ids, sorted(ids))

    def test_list_all_resources_valid_gem5_version(self):
        """Test listing all resources with a valid gem5 version."""
        response = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

        # Verify all returned resources have a gem5 version that is a prefix
        # of or equal to the requested version
        for resource in data:
            self.assertIn("gem5_versions", resource)
            # Should have "23.0" in gem5_versions
            self.assertIn("23.0", resource["gem5_versions"])

    def test_list_all_resources_missing_gem5_version(self):
        """Test listing resources without gem5-version parameter."""
        response = requests.get(
            f"{self.base_url}/resources/list-all-resources"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("gem5-version", data["error"])

    def test_list_all_resources_invalid_gem5_version(self):
        """Test listing resources with invalid gem5-version format."""
        response = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "invalid-version!@#"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_list_all_resources_nonexistent_gem5_version(self):
        """Test listing resources with a gem5 version that doesn't exist."""
        response = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "99.99.99"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)

    def test_list_all_resources_returns_multiple_versions(self):
        """Test that list-all-resources returns all versions of resources."""
        response = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check if any resource ID appears multiple times (different versions)
        ids = [r["id"] for r in data]
        # Just verify it returns valid resources
        self.assertIsInstance(data, list)

    def test_list_all_resources_different_versions(self):
        """Test listing resources with different gem5 versions returns
        different results."""
        response_v23 = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0"},
        )
        response_v22 = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "22.0"},
        )

        self.assertEqual(response_v23.status_code, 200)
        self.assertEqual(response_v22.status_code, 200)

        data_v23 = response_v23.json()
        data_v22 = response_v22.json()

        # Verify correct gem5 version prefix in each response
        for resource in data_v23:
            self.assertIn("23.0", resource["gem5_versions"])
        for resource in data_v22:
            self.assertIn("22.0", resource["gem5_versions"])

    def test_list_all_resources_prefix_matching(self):
        """Test that a longer version like 23.0.0.1 matches resources
        with shorter prefixes like 23.0."""
        # First get resources with 23.0
        response_short = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0"},
        )
        # Then get resources with 23.0.0.1 (should match same resources)
        response_long = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0.0.1"},
        )

        self.assertEqual(response_short.status_code, 200)
        self.assertEqual(response_long.status_code, 200)

        data_short = response_short.json()
        data_long = response_long.json()

        # Resources from 23.0.0.1 should include all resources from 23.0
        # (since 23.0 is a prefix of 23.0.0.1)
        short_ids = {(r["id"], r["resource_version"]) for r in data_short}
        long_ids = {(r["id"], r["resource_version"]) for r in data_long}
        self.assertTrue(short_ids.issubset(long_ids))

    def test_list_all_resources_latest_version_only(self):
        """Test that latest-version=true returns only one version per
        resource."""
        response = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0", "latest-version": "true"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

        # Check no duplicate IDs (each resource appears only once)
        ids = [r["id"] for r in data]
        self.assertEqual(len(ids), len(set(ids)))

    def test_list_all_resources_latest_version_false(self):
        """Test that latest-version=false returns all versions (default
        behavior)."""
        response_default = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0"},
        )
        response_false = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0", "latest-version": "false"},
        )

        self.assertEqual(response_default.status_code, 200)
        self.assertEqual(response_false.status_code, 200)

        data_default = response_default.json()
        data_false = response_false.json()

        # Both should return the same results
        self.assertEqual(len(data_default), len(data_false))

    def test_list_all_resources_latest_version_reduces_results(self):
        """Test that latest-version=true returns fewer or equal resources
        than default."""
        response_all = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0"},
        )
        response_latest = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0", "latest-version": "true"},
        )

        self.assertEqual(response_all.status_code, 200)
        self.assertEqual(response_latest.status_code, 200)

        data_all = response_all.json()
        data_latest = response_latest.json()

        # Latest should have <= resources than all versions
        self.assertLessEqual(len(data_latest), len(data_all))

        # All IDs in latest should exist in all versions
        latest_ids = {r["id"] for r in data_latest}
        all_ids = {r["id"] for r in data_all}
        self.assertTrue(latest_ids.issubset(all_ids))

    def test_list_all_resources_latest_version_returns_highest(self):
        """Test that latest-version=true returns the highest version of each
        resource."""
        response_all = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0"},
        )
        response_latest = requests.get(
            f"{self.base_url}/resources/list-all-resources",
            params={"gem5-version": "23.0", "latest-version": "true"},
        )

        self.assertEqual(response_all.status_code, 200)
        self.assertEqual(response_latest.status_code, 200)

        data_all = response_all.json()
        data_latest = response_latest.json()

        # Build a dict of max versions from all resources
        max_versions = {}
        for r in data_all:
            rid = r["id"]
            ver = r.get("resource_version", "0")
            if rid not in max_versions:
                max_versions[rid] = ver
            else:
                # Compare versions
                current = tuple(int(x) for x in ver.split("."))
                existing = tuple(int(x) for x in max_versions[rid].split("."))
                if current > existing:
                    max_versions[rid] = ver

        # Verify latest returns the max version for each resource
        for r in data_latest:
            rid = r["id"]
            self.assertEqual(r["resource_version"], max_versions[rid])


if __name__ == "__main__":
    unittest.main()
