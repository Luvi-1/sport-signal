"""Synthetic fixtures, configurations and mocked estimators; no numerical fits."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from experiments.tactical import football_model as model
from experiments.tactical import _soccer_football_common as common
from tests.test_tactical_football import fixtures


def features():
    return model.parser.build_panel(*fixtures(), 2023, include_targets=False).features


class FootballModelContractTests(unittest.TestCase):
    def test_exact_50_plan_and_fixed_grids(self):
        ops = model.planned_operations()
        self.assertEqual(len(ops), 50); self.assertEqual(len(set(ops)), 50)
        self.assertEqual(len(model.grid('logistic')), 3); self.assertEqual(len(model.grid('tree')), 8)
        self.assertEqual(len(model.A), 12); self.assertEqual(len(model.B), 23); self.assertEqual(len(model.C), 27)
        self.assertNotIn('formation_era', model.C)

    def test_fixed_basis_missing_values_and_overtime(self):
        x = features().astype(object)
        x.loc[0, ['qtr', 'half_seconds_remaining']] = [2, 120]
        x.loc[1, ['qtr', 'game_seconds_remaining', 'score_differential']] = [4, 300, -7]
        x.loc[2, ['qtr', 'half_seconds_remaining']] = [5, 10]
        x.loc[3, 'half_seconds_remaining'] = None
        b = model.basis(x, 'A')
        self.assertEqual(b.two_minute_half.iloc[:3].tolist(), [1., 0., 0.])
        self.assertEqual(b.late_game_score.iloc[1], -7)
        self.assertTrue(pd.isna(b.two_minute_half.iloc[3])); self.assertEqual(model._category('qtr', 5), 'OT')

    def test_missing_indicators_all_missing_and_fixed_vocabulary(self):
        x = features().astype(object); x['defense_dl'] = None
        matrix, state = model.fit_transform(x, 'C')
        i = state['numeric'].index('defense_dl'); self.assertEqual(state['medians'][i], 0.)
        self.assertEqual(state['scale'][i], 1.); self.assertIn('formation=PISTOL', state['columns'])
        self.assertIn('formation=UNKNOWN', state['columns']); self.assertIn('formation=MISSING', state['columns'])
        self.assertTrue((matrix[:, state['columns'].index('defense_dl__missing')] == 1).all())
        self.assertEqual(matrix.dtype, np.float64); self.assertEqual(len(state['columns']), matrix.shape[1])

    def test_inference_unknown_and_missing_are_distinct_and_no_vocabulary_fit(self):
        x = features().astype(object); _, state = model.fit_transform(x, 'C'); before = copy.deepcopy(state)
        x.loc[0, 'formation'] = 'FUTURE_LEGAL'; x.loc[1, 'formation'] = None
        transformed = model.transform(x, state)
        self.assertEqual(transformed[0, state['columns'].index('formation=UNKNOWN')], 1.)
        self.assertEqual(transformed[1, state['columns'].index('formation=MISSING')], 1.)
        self.assertEqual(state, before)

    def test_fit_preprocessing_is_training_only(self):
        x = features(); matrix, state = model.fit_transform(x, 'A'); future = x.copy(); future['ydstogo'] = 99
        before = copy.deepcopy(state); model.transform(future, state); self.assertEqual(state, before)
        np.testing.assert_allclose(matrix[:, :len(state['numeric'])].mean(axis=0), 0., atol=1e-12)

    def test_prohibited_future_fields_and_row_permutation_invariant(self):
        x = features(); matrix, state = model.fit_transform(x, 'C')
        changed = x.copy(); changed['epa'] = 99; changed['qb_dropback'] = 1; changed['formation_era'] = 'changed'; changed['passer_player_id'] = None
        np.testing.assert_array_equal(matrix, model.transform(changed, state))
        np.testing.assert_array_equal(matrix[::-1], model.transform(changed.iloc[::-1], state))

    def test_supplemental_join_reordering_invariant(self):
        p, part, ftn = fixtures()
        original = model.parser.build_panel(p, part, ftn, 2023, include_targets=False).features
        other = model.parser.build_panel(p, part.iloc[::-1], ftn.iloc[::-1], 2023, include_targets=False).features
        pd.testing.assert_frame_equal(original, other)

    def test_reference_jeffreys_and_hierarchical_shrinkage(self):
        x = features(); y = [0, 1, 0, 1]
        state = model.build_counts(x, y, 'context'); self.assertEqual(state['global'], .5)
        self.assertAlmostEqual(state['downs']['1'], 25/51)
        self.assertAlmostEqual(state['cells'][('1', '6-10')], 50*(25/51)/51)
        unseen = x.iloc[:1].copy(); unseen['ydstogo'] = 99
        self.assertEqual(model.count_prediction(unseen, state)[0], state['downs']['1'])
        self.assertEqual(model.distance_band(np.nan), 'MISSING')

    def test_ties_stronger_regularization_and_tree_complexity_order(self):
        for family in ('logistic', 'tree'):
            candidates = [{'config': c, 'status': 'complete', 'log_loss': .5} for c in model.grid(family)]
            chosen = model.select_candidate(family, candidates)['config']
            if family == 'logistic': self.assertEqual(chosen['C'], .1)
            else: self.assertEqual(chosen, {'learning_rate': .05, 'max_leaf_nodes': 7, 'l2_regularization': 10.})
            with self.assertRaises(ValueError): model.select_candidate(family, candidates[:-1])

    def test_public_numerical_paths_closed_without_gate(self):
        with tempfile.TemporaryDirectory() as td:
            for call in (model.develop, model.calibrate, model.predict):
                with self.subTest(call=call.__name__), self.assertRaises(PermissionError): call(Path(td))

    def test_source_role_checked_before_body_read(self):
        with patch.object(pd, 'read_csv') as read:
            with self.assertRaises(ValueError): model._verify_source(Path('/missing/play_by_play_2025.csv.gz'), 2023, 'pbp')
            with self.assertRaises(ValueError): model._verify_source(Path('/missing/fake.csv'), 2023, 'pbp')
            read.assert_not_called()

    def test_label_role_and_metadata_rejected_before_body(self):
        p, part, ftn = fixtures(); panel = model.parser.build_panel(p, part, ftn, 2023, include_targets=False)
        with patch.object(model, '_guard'), patch.object(pd, 'read_csv') as read:
            with self.assertRaises(PermissionError): model._labels('/missing', 'test', panel.metadata, 'develop')
            with self.assertRaises(ValueError): model._labels('/missing', 'selection', panel.metadata, 'develop')
            read.assert_not_called()

    def test_private_labels_guard_before_body(self):
        with patch.object(model, '_guard', side_effect=PermissionError()), patch.object(pd, 'read_csv') as read:
            with self.assertRaises(PermissionError): model._labels('/missing', 'initial', pd.DataFrame(), 'develop')
            read.assert_not_called()

    def test_fit_gated_before_any_preprocessing(self):
        with patch.object(model, 'fit_transform') as transform:
            with self.assertRaises(PermissionError): model._fit(features(), [0, 1, 0, 1], 'logistic', 'A', {'C': .1}, lambda: (_ for _ in ()).throw(PermissionError()))
            transform.assert_not_called()

    def test_tree_and_logistic_config_mocked_no_fit(self):
        x = features()
        for family, constructor in [('logistic', 'LogisticRegression'), ('tree', 'HistGradientBoostingClassifier')]:
            with patch.object(model, constructor) as estimator, patch.object(common, 'checked_fit', return_value='mocked'):
                result = model._fit(x, [0, 1, 0, 1], family, 'C', model.grid(family)[0], lambda: None)
                self.assertEqual(result['model'], 'mocked')
                kwargs = estimator.call_args.kwargs
                self.assertEqual(kwargs['class_weight'], None); self.assertFalse(kwargs['warm_start'])
                if family == 'tree': self.assertFalse(kwargs['early_stopping']); self.assertEqual(kwargs['max_iter'], 150)
                else: self.assertEqual(kwargs['tol'], 1e-6); self.assertEqual(kwargs['max_iter'], 2000)

    def test_serialization_and_single_row_transform_parity(self):
        x = features(); matrix, state = model.fit_transform(x, 'C')
        single = np.concatenate([model.transform(x.iloc[[i]], state) for i in range(len(x))])
        np.testing.assert_array_equal(matrix, single)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'model.joblib'; sha = common.save_object(path, state)
            np.testing.assert_array_equal(matrix, model.transform(x, common.load_object(path, sha)))

    def test_support_does_not_change_denominator(self):
        p, part, ftn = fixtures(); panel = model.parser.build_panel(p, part, ftn, 2023, include_targets=False)
        records = model.support_records(panel.features, panel.metadata)
        self.assertEqual(sum(r['plays'] for r in records), len(panel.features))
        self.assertTrue(all(r['games'] == 1 for r in records))

    def test_exact_score_conventions(self):
        report = common.summarize([0, 1], [.5, .5], ['a', 'b'], model.BINS)
        self.assertEqual(report['brier'], .25); self.assertEqual(report['accuracy'], .5)
        self.assertEqual(len(report['reliability']), 10)
        paired = common.paired([0, 1], [.2, .8], [.4, .6], ['a', 'b'])
        self.assertEqual(paired['log_loss']['seed'], 20261011)
        self.assertIn('linear', paired['log_loss']['interval_method'])
