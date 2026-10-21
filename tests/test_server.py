"""Unit tests for FastAPI endpoints: /api/analyze, /api/trace, and /api/contingency."""

import unittest
from fastapi.testclient import TestClient

from server.main import app


class TestServerEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.toy_text = "city council city council budget"

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

    def test_analyze_toy_example(self):
        """Toy example 'city council city council budget':
        Expected: N = 4, PMI of 'city council' = 1.0, chi-square = 4.0
        """
        payload = {
            "text": self.toy_text,
            "ngram": 2,
            "min_freq": 1,
            "metric": "pmi",
            "drop_stopwords": False,
            "top_k": 10,
            "use_full_corpus": False,
        }
        response = self.client.post("/api/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        stats = data["stats"]
        self.assertEqual(stats["n_bigrams"], 4)

        rankings = data["rankings"]
        self.assertTrue(len(rankings) > 0)

        # First ranking should be 'city council'
        top_phrase = rankings[0]
        self.assertEqual(top_phrase["phrase"], "city council")
        self.assertAlmostEqual(top_phrase["score"], 1.0, places=4)
        self.assertEqual(top_phrase["freq"], 2)

        # Check side-by-side chi_sq top-5
        top_chi = data["per_metric_top5"]["chi_sq"][0]
        self.assertEqual(top_chi["phrase"], "city council")
        self.assertAlmostEqual(top_chi["score"], 4.0, places=4)

    def test_trace_toy_example(self):
        """Verify pipeline trace generator produces 9 distinct stages for the toy example."""
        payload = {
            "text": self.toy_text,
            "sample_sentence_index": 0,
            "target_phrase": "city council",
            "drop_stopwords": False,
            "ngram": 2,
        }
        response = self.client.post("/api/trace", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["chosen_phrase"], "city council")
        self.assertEqual(len(data["stages"]), 9)

        stage_ids = [s["id"] for s in data["stages"]]
        expected_ids = [
            "raw_text",
            "sentence_split",
            "tokenize_clean",
            "lemmatize",
            "ngram_extraction",
            "counting",
            "contingency_table",
            "scoring",
            "ranking",
        ]
        self.assertEqual(stage_ids, expected_ids)

        # Stage 7 contingency table
        ct_stage = data["stages"][6]["data"]
        self.assertEqual(ct_stage["o11"], 2)
        self.assertEqual(ct_stage["o12"], 0)
        self.assertEqual(ct_stage["o21"], 0)
        self.assertEqual(ct_stage["o22"], 2)
        self.assertEqual(ct_stage["n"], 4)

        # Stage 8 scores
        scores_stage = data["stages"][7]["data"]["scores"]
        self.assertAlmostEqual(scores_stage["pmi"], 1.0, places=4)
        self.assertAlmostEqual(scores_stage["chi_sq"], 4.0, places=4)

    def test_contingency_endpoint(self):
        response = self.client.get(
            "/api/contingency",
            params={
                "w1": "city",
                "w2": "council",
                "text": self.toy_text,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["phrase"], "city council")
        self.assertEqual(data["o11"], 2)
        self.assertEqual(data["n"], 4)
        self.assertAlmostEqual(data["scores"]["pmi"], 1.0, places=4)
        self.assertAlmostEqual(data["scores"]["chi_sq"], 4.0, places=4)
        self.assertIn("pmi", data["formulas"])
        self.assertIn("chi_sq", data["formulas"])

    def test_sample_endpoints(self):
        response = self.client.get("/api/sample")
        self.assertEqual(response.status_code, 200)
        samples = response.json()
        self.assertIsInstance(samples, list)
        self.assertGreaterEqual(len(samples), 1)

        first_id = samples[0]["id"]
        detail_resp = self.client.get(f"/api/sample/{first_id}")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertTrue(len(detail_resp.json()["content"]) > 0)


if __name__ == "__main__":
    unittest.main()
