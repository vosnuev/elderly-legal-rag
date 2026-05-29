from __future__ import annotations

import unittest

from query.guard import QueryValidationError, validate_read_query, validate_write_query


class QueryGuardTest(unittest.TestCase):
    def test_read_query_appends_limit(self) -> None:
        result = validate_read_query("MATCH (n) RETURN n", max_rows=10)

        self.assertEqual(result.query, "MATCH (n) RETURN n LIMIT 10")
        self.assertEqual(result.access, "read_only")

    def test_read_query_blocks_write_operation(self) -> None:
        with self.assertRaises(QueryValidationError):
            validate_read_query("MERGE (n:Document {id: 'x'}) RETURN n", max_rows=10)

    def test_read_query_blocks_multiple_statements(self) -> None:
        with self.assertRaises(QueryValidationError):
            validate_read_query("MATCH (n) RETURN n; MATCH (m) RETURN m", max_rows=10)

    def test_internal_write_query_requires_job_metadata(self) -> None:
        with self.assertRaises(QueryValidationError):
            validate_write_query(
                "MERGE (n:Document {id: $id}) RETURN n",
                job_id="",
                purpose="ingest",
            )

    def test_internal_write_query_allows_idempotent_merge(self) -> None:
        result = validate_write_query(
            "MERGE (n:Document {id: $id}) RETURN n",
            job_id="job-1",
            purpose="ingest",
        )

        self.assertEqual(result.access, "read_write")


if __name__ == "__main__":
    unittest.main()
