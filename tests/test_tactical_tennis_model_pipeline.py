"""End-to-end synthetic reader/pipeline regressions, without estimator fitting."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from experiments.tactical import tennis_model as m
from test_tactical_tennis_model import raw


class FakeSource:
    future_target=2
    calls=[]
    dates=("20100101","20100122","20100123","20221210","20221211","20230101","20230102",
           "20231210","20231211","20240101","20240102","20241210","20241211","20250101","20250123","20251231")

    def __init__(self,root,permit):
        from collections import Counter
        self.permit=permit;self.read_log=Counter()
        self.keys=[("m",d+"-match") for d in self.dates]
        self.matches={k:{"Date":k[1][:8],"Tournament":"Synthetic Event"} for k in self.keys}
        self.quality={k:{"point_count":1} for k in self.keys}

    def read_match(self,key,*,purpose,analysis_date=None):
        day=self.matches[key]["Date"];self.permit.check(day,purpose,analysis_date)
        self.calls.append((self.permit.phase,day,purpose,analysis_date));self.read_log[purpose]+=1
        target=self.future_target if day>="20250101" else 0
        return {"A1":[(raw(day),target,False)],"A2":[(raw(day),target,False)]}

    def close(self):pass


class PipelineTests(unittest.TestCase):
    def load(self,root,stage):
        return m.Dataset(m.artifact_dir(root)/"rows"/stage/"A1_m",root=root,stage=stage)

    def test_complete_stream_preserves_history_and_late_year_membership(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(m,"SourceReader",FakeSource),patch("experiments.tactical.gates.require_stage"),patch.object(m,"verify_selection_freeze"):
            FakeSource.calls=[]
            dev=m.build_rows(directory,"development")
            train=self.load(directory,"train");selection=self.load(directory,"selection")
            self.assertEqual(train.n,4);self.assertEqual(selection.n,3)
            train_dates=[r["date"] for r in train.metadata()]
            self.assertNotIn("20221211",train_dates)
            # Source January 1 enters history strictly after January 22.
            np.testing.assert_allclose(train.baselines[1,0],np.ones(3)/3)
            self.assertGreater(train.baselines[2,0,0],1/3)
            self.assertTrue(all(day<"20240101" for _,day,_,_ in FakeSource.calls))
            cal=m.build_rows(directory,"calibration")
            calibration=self.load(directory,"calibration")
            self.assertEqual(calibration.n,3)
            self.assertNotIn("20241211",[r["date"] for r in calibration.metadata()])
            self.assertIn(("calibration","20231211","history","20240102"),FakeSource.calls)
            self.assertTrue(all(day<"20250101" for _,day,_,_ in FakeSource.calls))
            first=list(calibration.metadata())[0]
            self.assertFalse(first["server_cold"]);self.assertGreater(first["server_prior_points"],0)
            m.build_rows(directory,"evaluation",as_of="20260122")
            evaluation=self.load(directory,"evaluation")
            self.assertEqual(evaluation.n,3)
            self.assertIn(("evaluation","20241211","history","20250123"),FakeSource.calls)
            self.assertEqual(list(evaluation.metadata())[-1]["date"],"20251231")
            self.assertEqual(dev["unavailable_parameter_rows"]["train_late_or_unavailable_matches"],1)

    def test_future_target_mutation_leaves_development_digests_identical(self):
        results=[]
        for target in (0,2):
            with tempfile.TemporaryDirectory() as directory,patch.object(m,"SourceReader",FakeSource):
                FakeSource.future_target=target
                result=m.build_rows(directory,"development")
                results.append(result["datasets"])
        self.assertEqual(results[0],results[1])
        FakeSource.future_target=2

    def test_partial_evaluation_and_cache_cutoffs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for cutoff in ("20250701","20260121","20260123"):
                with self.assertRaises(PermissionError):m.evaluate(directory,as_of=cutoff)
                with self.assertRaises(PermissionError):m.ReadPermit("evaluation",cutoff)
            path=m.artifact_dir(directory)/"rows/evaluation/A1_m"
            writer=m.DatasetWriter(path,"A1",stage="evaluation",label_cutoff="20250701")
            writer.close()
            with patch("experiments.tactical.gates.require_stage"),patch.object(m,"verify_selection_freeze"):
                with self.assertRaises(PermissionError):self.load(directory,"evaluation")

    def test_day_start_snapshot_cannot_be_mutated_after_prediction(self):
        history=m.CellHistory()
        history.features(raw(),"A1")
        with self.assertRaises(ValueError):history.ingest("old","20220101",[(raw("20220101"),0)],"20230124")
        history.ingest("old","20220101",[(raw("20220101"),0)],"20230125")
        self.assertGreater(history.features(raw("20230125"),"A1")[2][0,0],1/3)

    def test_four_week_bootstrap_is_paired_and_keeps_empty_bins(self):
        dates=["20250101","20250201","20250301","20250401","20250501"]
        matches=["a","b","c","d","e"]
        result=m.moving_block_interval(np.full(5,-.01),dates,matches)
        self.assertEqual(result["calendar_bins"],53)
        self.assertEqual(result["populated_weeks"],5)
        # Sparse schedules can generate empty resamples; that is explicit.
        if result["interval"] is not None:np.testing.assert_allclose(result["interval"],[-.01,-.01])
        self.assertEqual(result,m.moving_block_interval(np.full(5,-.01),dates,matches))
        with self.assertRaises(ValueError):m.moving_block_interval(np.zeros(5),dates,["same"]*5)

    def test_event_resampling_keeps_match_macro_not_event_macro(self):
        result=m.event_match_macro_interval(np.array([0.]+[1.]*9),["m"+str(i) for i in range(10)],["small"]+["large"]*9)
        self.assertAlmostEqual(result["difference"],.9)
        self.assertNotAlmostEqual(result["difference"],.5)
        self.assertEqual(result["matches"],10)
        with self.assertRaises(ValueError):m.event_match_macro_interval(np.array([0.,1.]),["same","same"],["one","two"])

    def test_common_case_metrics_brier_sum_and_sparse_bins(self):
        metadata=[dict(match_id="match"+str(i),server="A",server_prior_points=0,returner_prior_points=0,server_side_prior_points=0) for i in range(3)]
        p=np.tile(np.array([.5,.25,.25]),(3,1));labels=np.array([0,1,2])
        result=m.performance_summary(labels,p,metadata)
        expected=np.mean(np.sum((p-np.eye(3))**2,axis=1))
        self.assertAlmostEqual(result["brier"],expected)
        self.assertEqual(len(result["reliability"]),30)
        self.assertTrue(all(b["sparse"] for b in result["reliability"]))
        self.assertEqual(result["b0_fallback_fraction"],1.)


if __name__=="__main__":unittest.main()


class AllCellSource(FakeSource):
    calibration_observed_freeze=False
    def __init__(self,root,permit):
        super().__init__(root,permit)
        self.keys=[(corpus,d+"-"+corpus+"-match") for d in self.dates for corpus in "mw"]
        self.matches={k:{"Date":k[1][:8],"Tournament":"Synthetic Event"} for k in self.keys}
        self.quality={k:{"point_count":1} for k in self.keys}
        if permit.phase=="calibration":
            assert (m.artifact_dir(root)/"CANDIDATE_FREEZE.json").exists()
            self.__class__.calibration_observed_freeze=True


class MockEstimator:
    """No numerical estimation. A fixed three-class distribution for wiring tests."""
    def __init__(self,family,parameter,**kw):self.family=family;self.parameter=parameter
    def fit(self,X,y):self.classes_=np.arange(3);return self
    def predict_proba(self,X):return np.tile(np.array([.5,.25,.25]),(X.shape[0],1))
    def get_params(self):return {"family":self.family,"parameter":self.parameter}
    def set_params(self,**kw):return self


class OrchestrationTests(unittest.TestCase):
    def test_full_four_cell_mocked_development_freezes_before_calibration(self):
        from types import SimpleNamespace
        snapshots=[]
        for future in (0,2):
            with tempfile.TemporaryDirectory() as directory:
                dest=m.artifact_dir(directory);dest.mkdir(parents=True)
                (dest/"run_binding.json").write_text('{"binding_sha256":"synthetic"}')
                # _freeze records the protocol hash; this synthetic file has no authority.
                protocol=Path(directory)/m.PROTOCOL;protocol.parent.mkdir(parents=True);protocol.write_text("synthetic unit fixture")
                AllCellSource.future_target=future;AllCellSource.calls=[];AllCellSource.calibration_observed_freeze=False
                sufficient={"sufficient":True,"n":3000,"matches":50,"class_counts":[1000,1000,1000]}
                with patch.object(m,"SourceReader",AllCellSource),patch.object(m,"make_estimator",side_effect=MockEstimator),\
                     patch.object(m.Dataset,"supports",return_value=sufficient),\
                     patch.object(m,"minimize_scalar",return_value=SimpleNamespace(success=True,x=0.,fun=1.,nfev=1)),\
                     patch("experiments.tactical.gates.require_stage"),patch("experiments.tactical.gates.record_operation"),\
                     patch("experiments.tactical.gates.verify_binding",return_value={"binding_sha256":"synthetic"}):
                    result=m.develop(directory,run_probe=False)
                    self.assertTrue(AllCellSource.calibration_observed_freeze)
                    self.assertEqual(set(result["cells"]),{"A1_m","A1_w","A2_m","A2_w"})
                    self.assertEqual(result["optimizer_attempts"],24)  # 12 fixed L stubs + 12 temperature stubs
                    self.assertTrue(all(v["status"]=="frozen" for v in result["cells"].values()))
                    self.assertTrue(all(day<"20250101" for _,day,_,_ in AllCellSource.calls))
                    self.assertTrue((dest/"resource_totals.json").exists())
                    snapshots.append({key:{"main":value["designated_main"],"selected":value["selected_parameters"],
                                           "temperatures":value["temperatures"],"calibration_data":value["calibration_data"]} for key,value in result["cells"].items()})
        self.assertEqual(snapshots[0],snapshots[1])

    def test_self_rehashed_cache_disagrees_with_parent_manifest(self):
        import json
        with tempfile.TemporaryDirectory() as directory,patch.object(m,"SourceReader",FakeSource),patch("experiments.tactical.gates.require_stage"):
            m.build_rows(directory,"development")
            path=m.artifact_dir(directory)/"rows/train/A1_m"
            manifest=json.loads((path/"manifest.json").read_text());manifest["label_sha256"]="rehash"
            m.write_json(path/"manifest.json",manifest)
            with self.assertRaises(PermissionError):m.Dataset(path,root=directory,stage="train")

    def test_final_stage_budget_includes_after_fit_work(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=m.AttemptLedger(Path(directory)/"attempts.json")
            ledger.prior_stage_cpu=5401
            with self.assertRaises(m.BudgetExceeded):ledger.check_budget()


class CacheLineageTests(unittest.TestCase):
    def fixture(self,root):
        import json
        paths=["experiments/tactical/tennis.py","docs/research/tennis/source_manifest.json",
               "data/tactical/tennis/source_index.sqlite3","data/tactical/tennis/match_quality.jsonl"]
        for relative in paths:
            path=Path(root)/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text("synthetic "+relative)
        provenance={"manifest_sha256":m.tennis.digest(Path(root)/paths[1]),"parser_code_sha256":m.tennis.digest(Path(root)/paths[0]),
                    "commit":"synthetic","files":[{"file":"fixture.csv","sha256":"synthetic raw hash"}]}
        summary="reports/tactical/tennis/summary.json"
        m.write_json(Path(root)/summary,{"provenance":provenance})
        review="docs/tactical/INDEPENDENT_STAGE_ONE_REVIEW_MANIFEST.json"
        m.write_json(Path(root)/review,{"files_sha256":{p:m.tennis.digest(Path(root)/p) for p in (paths[0],paths[1],summary)}})
        anchor={"schema_version":1,"status":"independently_verified","reviewed_utc":"synthetic test",
                "lineage_verification":"Synthetic fixture only, no source permission",
                "source_manifest_sha256":provenance["manifest_sha256"],"parser_code_sha256":provenance["parser_code_sha256"],
                "raw_files_sha256":{"fixture.csv":"synthetic raw hash"},"independent_review_manifest_sha256":m.tennis.digest(Path(root)/review),
                "files_sha256":{p:m.tennis.digest(Path(root)/p) for p in (paths[2],paths[3],summary)}}
        return provenance,anchor

    def test_missing_or_changed_derivative_anchor_is_not_blessed(self):
        with tempfile.TemporaryDirectory() as directory:
            provenance,anchor=self.fixture(directory)
            with self.assertRaises(PermissionError):m.verify_source_cache_lineage(directory,provenance)
            m.write_json(m.artifact_dir(directory)/"SOURCE_CACHE_REVIEW.json",anchor)
            self.assertIn("data/tactical/tennis/source_index.sqlite3",m.verify_source_cache_lineage(directory,provenance))
            (Path(directory)/"data/tactical/tennis/source_index.sqlite3").write_text("changed derivative")
            with self.assertRaises(PermissionError):m.verify_source_cache_lineage(directory,provenance)

    def test_stale_summary_parser_lineage_rejected(self):
        import copy
        with tempfile.TemporaryDirectory() as directory:
            provenance,anchor=self.fixture(directory)
            m.write_json(m.artifact_dir(directory)/"SOURCE_CACHE_REVIEW.json",anchor)
            changed=copy.deepcopy(provenance);changed["parser_code_sha256"]="new parser"
            with self.assertRaises(PermissionError):m.verify_source_cache_lineage(directory,changed)
