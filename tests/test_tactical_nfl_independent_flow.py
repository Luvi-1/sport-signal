"""Independent synthetic NFL orchestration audit; no real data or estimator fit."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.special import expit

from experiments.tactical import football_model as runner
from experiments.tactical import _soccer_football_common as common
from tests.test_tactical_football_model import features


class FixedMockEstimator:
    """Fixed response function, with no fit method or learned parameters."""
    classes_ = np.array([0, 1])
    coef_ = np.array([[1.]])
    intercept_ = np.array([0.])

    def predict_proba(self, matrix):
        probability = expit(np.asarray(matrix)[:, 0] * .1)
        return np.column_stack([1 - probability, probability])


class IndependentNFLFlowTests(unittest.TestCase):
    def test_full_mocked_flow_budget_role_order_and_saved_score_recomputation(self):
        reads, estimations = [], []

        def fake_checked_fit(estimator, matrix, labels, guard):
            guard()
            estimations.append((type(estimator).__name__, len(labels), matrix.shape))
            return FixedMockEstimator()

        def fake_labels(root, role, metadata, stage, *args, **kwargs):
            reads.append((stage, role))
            return np.array([0, 1, 1, 0], dtype=np.int64)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / 'artifacts/tactical/football/model'
            output.mkdir(parents=True)
            roles = {}
            for role, (season, first_week, last_week) in runner.ROLES.items():
                metadata = pd.DataFrame({
                    'game_id': [f'{season}g0'] * 2 + [f'{season}g1'] * 2,
                    'play_id': [1, 2, 1, 2],
                    'week': [first_week] * 2 + [last_week] * 2,
                    'season': [season] * 4, 'season_type': ['REG'] * 4,
                    'posteam': ['A', 'A', 'B', 'B'],
                })
                roles[role] = {'metadata': metadata, 'features': features()}
            prepared = {'synthetic': True, 'split_sha256': 'synthetic'}
            # Gate denial/source identity have separate adversarial tests. This
            # fixture exercises the approved wiring without creating any real approval.
            with patch.object(runner, '_prepared', return_value=(output, prepared, roles)), \
                 patch.object(runner, '_guard'), \
                 patch.object(runner, '_labels', side_effect=fake_labels), \
                 patch.object(common, 'checked_fit', side_effect=fake_checked_fit), \
                 patch('experiments.tactical.gates.record_operation'):
                runner.develop(root)
                self.assertEqual(reads, [('develop', 'initial'), ('develop', 'selection')])
                self.assertEqual(len(estimations), 39)
                self.assertTrue((output / 'DEVELOPMENT_FREEZE.json').exists())
                runner.calibrate(root)
                self.assertEqual(len(estimations), 46)
                self.assertEqual(reads[-1], ('calibrate', 'calibration'))
                common.verify_development(output, common.digest(prepared), runner.planned_operations())
                runner.predict(root)
                self.assertEqual(reads[-1], ('calibrate', 'calibration'))
                report = runner.evaluate(root)
                self.assertEqual(reads[-1], ('evaluate', 'test'))

            attempts = json.loads((output / 'operations/operations.json').read_text())['attempts']
            self.assertEqual(len(attempts), 50)
            self.assertTrue(all(record['status'] == 'complete' for record in attempts))
            predictions = pd.DataFrame(json.loads((output / 'test_predictions.json').read_text()))
            labels = np.array([0, 1, 1, 0])
            self.assertEqual(len(report['procedures']), 15)
            for name, score in report['procedures'].items():
                probability = predictions[name].to_numpy()
                clipped = np.clip(probability, 1e-6, 1 - 1e-6)
                direct_loss = float((-labels * np.log(clipped) - (1-labels) * np.log(1-clipped)).mean())
                direct_brier = float(((probability-labels) ** 2).mean())
                self.assertAlmostEqual(score['log_loss'], direct_loss, places=12)
                self.assertAlmostEqual(score['brier'], direct_brier, places=12)


if __name__ == '__main__':
    unittest.main()
