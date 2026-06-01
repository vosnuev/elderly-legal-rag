from __future__ import annotations

import unittest

from neo4j.time import Date, DateTime, Duration, Time

from external.memgraph.client import _serialize_value


class MemgraphClientSerializationTest(unittest.TestCase):
    def test_serializes_neo4j_temporal_values_for_json_responses(self) -> None:
        value = {
            "created_at": DateTime(2026, 6, 1, 12, 30, 45, 123456789),
            "business_date": Date(2026, 6, 1),
            "clock": Time(12, 30, 45, 123456789),
            "duration": Duration(months=1, days=2, seconds=3),
        }

        self.assertEqual(
            _serialize_value(value),
            {
                "created_at": "2026-06-01T12:30:45.123456789",
                "business_date": "2026-06-01",
                "clock": "12:30:45.123456789",
                "duration": "P1M2DT3S",
            },
        )


if __name__ == "__main__":
    unittest.main()
