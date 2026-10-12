"""Synthetic metadata/probabilities only. No estimator is fitted in this suite."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from experiments.tactical import soccer_model as model
from experiments.tactical import _soccer_football_common as common


def row(i=0, **updates):
    value = {'event_id': str(i), 'match_id': i//2+1, 'season_id': 4, 'match_date': '2018-09-01', 'cohort': 'development',
             'features': {'distance_native': 8.+i, 'goal_angular_width_rad': .6, 'goal_bearing_rad': -.2,
                          'lateral_offset_native': 2., 'body_part': 'Right Foot', 'shot_type': 'Open Play', 'play_pattern': 'Regular Play',
                          'keeper_depth_native': 1., 'keeper_lateral_offset_native': -2., 'nearest_recorded_opponent_native': 3.,
                          'recorded_outfield_in_goal_triangle': 1},
             'quality': {'recorded_opposition_keeper_count': 1, 'invalid_recorded_player_locations': 0,
                         'unknown_teammate_flags': 0, 'unknown_opponent_role_count': 0}}
    value.update(updates); return value


class SoccerModelContractTests(unittest.TestCase):
    def test_source_manifest_empty_or_changed_fails_before_context_parse(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); path=root/'data/tactical/soccer/source_manifest.json'
            path.parent.mkdir(parents=True);path.write_text(json.dumps({'commit':model.parser.COMMIT,'files':[]}))
            with self.assertRaises(ValueError):model.verified_source_index(root)

    def test_context_must_match_unique_source_match_season_and_date(self):
        r=row(); index={r['match_id']:(4,'2018-09-01','development')}
        model.verify_context_lineage([r],index)
        for key,value in [('season_id',42),('match_date','2018-09-02'),('match_id',999)]:
            changed=copy.deepcopy(r);changed[key]=value
            with self.assertRaises(ValueError):model.verify_context_lineage([r,changed],index)

    def test_independent_scoring_rejects_shared_metric_error(self):
        with patch.object(common.metrics,'classification_summary',return_value={'log_loss':999,'brier':999}):
            with self.assertRaises(ArithmeticError):common.summarize([0,1],[.2,.7],['a','b'],[0,.5,1])

    def test_24_operations_exact_grid(self):
        ops = model.planned_operations()
        self.assertEqual(len(ops), 24); self.assertEqual(len(set(ops)), 24)
        self.assertEqual(sum(o.startswith('inner_') for o in ops), 18)

    def test_cohorts_reject_unknown_flags_and_missing_keeper_without_clipping(self):
        r = row(); self.assertTrue(model.cohort_flags(r)['matched'])
        for key in ('invalid_recorded_player_locations', 'unknown_teammate_flags', 'unknown_opponent_role_count'):
            r2 = copy.deepcopy(r); r2['quality'][key] = 1
            self.assertTrue(model.cohort_flags(r2)['full']); self.assertFalse(model.cohort_flags(r2)['matched'])
        r['quality']['recorded_opposition_keeper_count'] = 0
        self.assertFalse(model.cohort_flags(r)['matched'])
        r['features']['goal_angular_width_rad'] = None
        self.assertFalse(model.cohort_flags(r)['full'])

    def test_training_only_preprocessing_and_unknown_onehot(self):
        rows = [row(0), row(1)]
        x, state = model.fit_transform(rows)
        np.testing.assert_allclose(x[:, :4].mean(axis=0), 0., atol=1e-12)
        new = row(20); new['features']['shot_type'] = 'FutureLegalLevel'
        before = copy.deepcopy(state); y = model.transform([new], state)
        self.assertEqual(state, before)
        index = state['columns'].index('shot_type=Open Play'); self.assertEqual(y[0, index], 0)
        self.assertNotIn('recorded_opponent_count', str(state))
        self.assertEqual(len(state['columns']), x.shape[1]); self.assertEqual(x.dtype, np.float64)

    def test_bearing_missing_indicator_and_no_binary_standardization(self):
        rows = [row(0), row(1)]; rows[0]['features']['goal_bearing_rad'] = None
        x, state = model.fit_transform(rows)
        self.assertEqual(x[:, state['columns'].index('bearing_missing')].tolist(), [1., 0.])

    def test_mirror_geometry_uses_absolute_values(self):
        left, right = row(0), row(0)
        for name in ('goal_bearing_rad', 'lateral_offset_native', 'keeper_lateral_offset_native'):
            right['features'][name] *= -1
        x, _ = model.fit_transform([left, right], True)
        np.testing.assert_array_equal(x[0], x[1])

    def test_fixed_cell_endpoints_and_unseen_cell(self):
        r = row(); r['features']['distance_native'] = 6; r['features']['goal_angular_width_rad'] = .25
        self.assertEqual(model.cell(r), (1, 1, 'Foot'))
        state = model.build_baselines([r], [1]); self.assertAlmostEqual(state['global_rate'], 2/3)
        unseen = row(100); self.assertEqual(model.baseline_prediction([unseen], state, 'B')[0], state['global_rate'])

    def test_tie_chooses_smallest_c(self):
        self.assertEqual(model.select_c({.1: .5000009, 1.: .5, 10.: .6}), .1)

    def test_role_cannot_disagree_with_metadata(self):
        with self.assertRaises(ValueError): model.role(row(season_id=281, match_date='2024-03-01'))

    def test_unknown_nonbinary_targets_stop_not_drop(self):
        for target in (None, float('nan'), 2, '1', -1):
            with self.subTest(target=target), self.assertRaises(ValueError): common.binary_targets([0, target, 1])

    def test_develop_and_calibrate_closed_without_approval(self):
        with tempfile.TemporaryDirectory() as td:
            for call in (model.develop, model.calibrate, model.predict):
                with self.subTest(call=call.__name__), self.assertRaises(PermissionError): call(Path(td))

    def test_private_target_reader_calls_guard_before_read(self):
        with patch.object(model, '_guard', side_effect=PermissionError('closed')), patch.object(Path, 'read_text') as read:
            with self.assertRaises(PermissionError): model._labels('/missing', [row()], 'develop', None)
            read.assert_not_called()

    def test_calibration_identity_insufficient_support_does_not_optimize(self):
        with patch.object(model, 'minimize') as optimize:
            result = model._calibration_fit(np.array([0, 1]), [.2, .8], lambda: None)
            self.assertEqual(result['status'], 'identity_insufficient_support'); optimize.assert_not_called()

    def test_fit_gated_before_transform_or_estimator(self):
        with patch.object(model, 'fit_transform') as transform:
            with self.assertRaises(PermissionError): model._fit([row()], [0], .1, False, lambda: (_ for _ in ()).throw(PermissionError()))
            transform.assert_not_called()

    def test_single_class_fallback_does_not_call_estimator(self):
        with patch.object(model, 'LogisticRegression') as estimator:
            artifact = model._fit([row(0), row(1)], np.array([1, 1]), .1, False, lambda: None)
            self.assertEqual(artifact['constant'], .75); estimator.assert_not_called()

    def test_common_brier_unclipped_logloss_clipped_and_bins_exact(self):
        report = common.summarize([0, 1], [1., 0.], ['a', 'b'], model.BINS, 50)
        self.assertEqual(report['brier'], 1.); self.assertAlmostEqual(report['log_loss'], -np.log(1e-6), places=8)
        self.assertEqual(len(report['reliability']), 6)
        self.assertTrue(all(r['low_support'] for r in report['reliability']))

    def test_future_and_forbidden_mutation_does_not_change_features(self):
        rows = [row(0), row(1)]; x, state = model.fit_transform(rows, True)
        changed = copy.deepcopy(rows)
        for r in changed:
            r['goal'] = 1; r['features']['statsbomb_xg'] = .99; r['features']['shot_endpoint'] = [120, 40]
            r['features']['recorded_opponent_count'] = 400
        np.testing.assert_array_equal(x, model.transform(changed, state))
        np.testing.assert_array_equal(x[::-1], model.transform(list(reversed(changed)), state))

    def test_serialization_parity_on_synthetic_transform(self):
        x, state = model.fit_transform([row(0), row(1)], True)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'state.joblib'; sha = common.save_object(path, state)
            loaded = common.load_object(path, sha); np.testing.assert_array_equal(x, model.transform([row(0), row(1)], loaded))
            with self.assertRaises(ValueError): common.load_object(path, '0'*64)

    def test_ledger_preserves_success_and_rejects_new_signature(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = common.OperationLedger(td, ['fit'])
            seen = []
            self.assertEqual(ledger.run('fit', 'fixed', lambda: seen.append(1) or {'ok': True}, lambda: None), {'ok': True})
            ledger.run('fit', 'fixed', lambda: seen.append(2), lambda: None); self.assertEqual(seen, [1])
            with self.assertRaises(ValueError): ledger.run('fit', 'changed', lambda: None, lambda: None)
