"""Offline Laya protocol checks; torch, model weights and network are unnecessary."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from scripts.evaluate_laya import (
    FEATURES, SPORTS, freeze, labels_for, probabilities, question, state_for, validate_cached,
)


class LayaProtocolTests(unittest.TestCase):
    def test_inputs_blind_identity_dates_and_target(self):
        row = {name: .125 for name in FEATURES}
        for field in ("event_id", "side_a", "side_b", "date", "available_date", "target"):
            row[field] = "secret value"
        original = state_for(row, "soccer")
        self.assertNotIn("secret value", original)
        for field in ("event_id", "side_a", "side_b", "date", "available_date", "target"):
            row[field] = "changed value"
        self.assertEqual(original, state_for(row, "soccer"))
        self.assertNotIn("changed value", original)

    def test_fixed_schema_and_label_mapping(self):
        self.assertEqual(labels_for("soccer"), ["side_b_win", "draw", "side_a_win"])
        for sport in SPORTS:
            q = question(sport)
            self.assertEqual(list(q["outcome"]["criteria"]), labels_for(sport))
            self.assertEqual(list(question(sport, True)["outcome"]["criteria"]), labels_for(sport)[::-1])
            self.assertEqual(q["outcome"]["type"], "choice")

    @staticmethod
    def result(values):
        return {"answers": {"outcome": {"probabilities": values}}}

    def test_sdk_rounding_is_bounded_and_normalized(self):
        labels = labels_for("soccer")
        p = probabilities(self.result(dict(zip(labels, [.3333] * 3))), labels)
        np.testing.assert_allclose(p, [1 / 3] * 3)
        self.assertAlmostEqual(p.sum(), 1.0)
        with self.assertRaises(ValueError):
            probabilities(self.result(dict(zip(labels, [.33] * 3))), labels)

    def test_invalid_probabilities_are_rejected(self):
        labels = labels_for("baseball")
        for values in ([float("nan"), 1], [float("inf"), 0], [-.1, 1.1], [.8, .8]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                probabilities(self.result(dict(zip(labels, values))), labels)
        with self.assertRaises(ValueError):
            probabilities(self.result({"other": 1}), labels)

    def test_nonfinite_features_are_rejected(self):
        row = {name: 0.0 for name in FEATURES}
        row[FEATURES[0]] = np.nan
        with self.assertRaises(ValueError):
            state_for(row, "football")

    def test_cached_records_fail_closed(self):
        labels = labels_for("tennis")
        record = {"event_id": "a", "target": 1, "labels": labels,
                  "probabilities": [.4, .6], "seconds": 1.0, "manifest_sha256": "sha"}
        np.testing.assert_allclose(validate_cached(record, labels, "a", 1, "sha"), [.4, .6])
        mutations = {"event_id": "b", "target": 0, "labels": labels[::-1],
                     "probabilities": [float("nan"), .6], "seconds": -1, "manifest_sha256": "other"}
        for key, value in mutations.items():
            broken = copy.deepcopy(record)
            broken[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_cached(broken, labels, "a", 1, "sha")

    def test_selection_is_deterministic_and_outcome_independent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "artifacts" / "soccer"
            data.mkdir(parents=True)
            f = pd.DataFrame({"event_id": [f"id{i:03}" for i in range(50)],
                              "date": pd.date_range("2024-01-01", periods=50).astype(str),
                              "target": np.arange(50) % 3})
            features = f.assign(**{name: 0.0 for name in FEATURES})
            features.to_csv(data / "features.csv", index=False)
            f.iloc[::-1].to_csv(data / "holdout_predictions.csv", index=False)
            first, spec = freeze(root, ["soccer"], 10)
            expected = [f"id{i:03}" for i in np.linspace(0, 49, 10, dtype=int)]
            self.assertEqual(first["soccer"].event_id.tolist(), expected)
            second, repeated = freeze(root, ["soccer"], 10)
            self.assertEqual(spec, repeated)
            # Independent root with permuted labels must choose the same events.
            other = root / "other"
            d2 = other / "artifacts" / "soccer"
            d2.mkdir(parents=True)
            features["target"] = 2 - features.target
            f["target"] = 2 - f.target
            features.to_csv(d2 / "features.csv", index=False)
            f.to_csv(d2 / "holdout_predictions.csv", index=False)
            permuted, _ = freeze(other, ["soccer"], 10)
            self.assertEqual(permuted["soccer"].event_id.tolist(), expected)
            # Changed underlying files cannot silently rewrite the original manifest.
            features.to_csv(data / "features.csv", index=False)
            f.to_csv(data / "holdout_predictions.csv", index=False)
            with self.assertRaises(ValueError):
                freeze(root, ["soccer"], 10)


if __name__ == "__main__":
    unittest.main()
