"""Synthetic numerical scoring tests, no trained models or provider rows."""
import unittest
import numpy as np
from experiments.tactical.metrics import classification_summary, per_case_scores, paired_cluster_interval, validate_probabilities

class TacticalMetricTests(unittest.TestCase):
    def test_binary_brier_and_log_loss_hand_calculation(self):
        result=classification_summary(np.array([0,1]),np.array([.25,.75]))
        self.assertAlmostEqual(result['brier'],.0625)
        self.assertAlmostEqual(result['log_loss'],-np.log(.75))
        self.assertEqual(result['accuracy'],1)
    def test_multiclass_brier_is_sum_not_mean(self):
        result=classification_summary(np.array([1]),np.array([[.2,.5,.3]]))
        self.assertAlmostEqual(result['brier'],.38)
        self.assertAlmostEqual(result['log_loss'],-np.log(.5))
        self.assertEqual(len(result['reliability']),30)
    def test_probabilities_fail_closed(self):
        for p in [[float('nan')],[-.1],[[.2,.3]],[[.5,.6]]]:
            with self.assertRaises(ValueError):validate_probabilities(np.array([0]),p)
        with self.assertRaises(ValueError):validate_probabilities(np.array([None]),[.5])
        with self.assertRaises(ValueError):validate_probabilities(np.array([2]),[.5])
    def test_zero_one_finite_loss_and_probability_one_bin(self):
        scores=per_case_scores(np.array([0,1]),np.array([1.,0.]))
        self.assertTrue(np.isfinite(scores['log_loss']).all())
        result=classification_summary(np.array([0,1]),np.array([0.,1.]))
        self.assertEqual(result['reliability'][9]['n'],1)
    def test_exact_protocol_clipping_and_bins(self):
        result=classification_summary(np.array([0,1]),np.array([1.,0.]),epsilon=1e-6,bin_edges=[0,.05,.2,1])
        self.assertAlmostEqual(result['log_loss'],-np.log(1e-6),places=9)
        self.assertEqual(result['brier'],1.)
        self.assertEqual(len(result['reliability']),6)
        with self.assertRaises(ValueError):classification_summary(np.array([1]),[.5],bin_edges=[0,.2,.1,1])
    def test_cluster_interval_deterministic_and_paired(self):
        difference=np.linspace(-.1,.2,60);groups=np.repeat(np.arange(20),3)
        a=paired_cluster_interval(difference,groups)
        b=paired_cluster_interval(difference,groups)
        self.assertEqual(a,b);self.assertEqual(a['status'],'computed')
        self.assertAlmostEqual(a['difference'],difference.mean())
        zero=paired_cluster_interval(np.zeros(60),groups)
        self.assertEqual(zero['interval'],[0.,0.])
    def test_small_groups_have_no_confidence_interval(self):
        result=paired_cluster_interval(np.ones(50),np.repeat(np.arange(5),10))
        self.assertIsNone(result['interval']);self.assertEqual(result['groups'],5)
    def test_case_and_group_weighting_differ(self):
        differences=np.r_[np.zeros(10),1.]
        groups=np.r_[np.zeros(10,dtype=int),1]
        self.assertAlmostEqual(paired_cluster_interval(differences,groups)['difference'],1/11)
        self.assertAlmostEqual(paired_cluster_interval(differences,groups,weighting='group')['difference'],.5)

if __name__=='__main__':unittest.main()
