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

    # EDGE CASE AND STRESS TESTS
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


if __name__ == "__main__":
    unittest.main()
