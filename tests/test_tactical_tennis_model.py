"""Synthetic/mocked tests only. Never fit an estimator on source data."""
import copy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock

import numpy as np
from scipy import sparse
from sklearn.exceptions import ConvergenceWarning

from experiments.tactical import tennis_model as m


def raw(day="20230124",server="A",returner="B",**extra):
    result={"match_date":day,"surface":"Hard","serve_side":"deuce","server":server,"returner":returner,
            "server_hand":"R","returner_hand":"L","current_tiebreak":False,"server_points":"0","returner_points":"15",
            "server_sets":0,"returner_sets":0,"server_games":0,"returner_games":0,"game_number":1,"point_ordinal":1,
            "first_fault_direction":"wide","first_fault_direction_status":"known","first_fault_type":"net"}
    result.update(extra);return result


def add(history,day="20230101",analysis="20230124",target=0,match="past",**kw):
    history.ingest(match,day,[(raw(day,**kw),target)],analysis)


class AvailabilityTests(unittest.TestCase):
    def test_strict_21_day_boundary(self):
        h=m.CellHistory()
        with self.assertRaises(ValueError):add(h,analysis="20230122")
        add(h,analysis="20230123")
        np.testing.assert_array_equal(h.global_counts,[1,0,0])

    def test_multiday_match_not_admitted_too_early(self):
        h=m.CellHistory()
        for day in ("20100623","20100624","20100713"):
            with self.assertRaises(ValueError):add(h,day="20100622",analysis=day)
        add(h,day="20100622",analysis="20100714")

    def test_parameter_year_end_boundaries(self):
        for stage,year in (("train",2022),("selection",2023),("calibration",2024)):
            self.assertTrue(m.stage_eligible(f"{year}1210",stage))
            self.assertFalse(m.stage_eligible(f"{year}1211",stage))
            self.assertFalse(m.stage_eligible(f"{year}1231",stage))
            self.assertFalse(m.stage_eligible(f"{year+1}0101",stage))
        self.assertFalse(m.stage_eligible("20091231","train"))

    def test_late_december_evaluation_waits_until_january(self):
        self.assertFalse(m.stage_eligible("20251231","evaluation",as_of="20260121"))
        self.assertTrue(m.stage_eligible("20251231","evaluation",as_of="20260122"))
        with self.assertRaises(ValueError):m.stage_eligible("20250101","evaluation")

    def test_late_december_history_without_reassignment(self):
        permit=m.ReadPermit("calibration")
        with self.assertRaises(PermissionError):permit.check("20231220","parameter")
        with self.assertRaises(PermissionError):permit.check("20231220","history","20240110")
        permit.check("20231220","history","20240111")
        h=m.CellHistory();add(h,day="20231220",analysis="20240111")
        np.testing.assert_array_equal(h.global_counts,[1,0,0])

    def test_parameter_future_labels_blocked(self):
        dev=m.ReadPermit("development")
        for day in ("20241201","20250101","20260101","20091231","20231225"):
            with self.assertRaises(PermissionError):dev.check(day,"parameter")
        dev.check("20231210","parameter")
        for phase in ("development","calibration"):
            with self.assertRaises(PermissionError):m.ReadPermit(phase).check("20250101","history","20250124")

    def test_whole_match_not_current_point_updates(self):
        h=m.CellHistory();add(h)
        earlier=h.features(raw(),"A1")
        with self.assertRaises(ValueError):add(h,day="20230124",analysis="20230124",match="current",target=2)
        later=h.features(raw(point_ordinal=20),"A1")
        np.testing.assert_allclose(earlier[2],later[2])
        with self.assertRaises(ValueError):add(h)

    def test_date_quarantine_is_preserved(self):
        self.assertIn("20210701-M-Wimbledon-QF-Hubert_Hurkacz-Roger_Federer",m.tennis.KNOWN_DATE_QUARANTINES)
        h=m.CellHistory();h.ingest("bad","20200101",[(raw(),0)],"20210101",accepted=False)
        np.testing.assert_array_equal(h.global_counts,[0,0,0])


class HistoryAndFeaturesTests(unittest.TestCase):
    def test_cold_fallback_is_exact_b0(self):
        h=m.CellHistory();add(h)
        nums,cats,baselines,audit=h.features(raw(server="new",returner="also new"),"A1")
        for p in baselines:np.testing.assert_array_equal(p,baselines[0])
        np.testing.assert_array_equal(nums[11:14],baselines[0]);np.testing.assert_array_equal(nums[14:17],baselines[0])
        np.testing.assert_array_equal(nums[17:],[0,0,0,0]);self.assertEqual(audit["server_prior_points"],0)

    def test_exact_b0_and_two_level_b1_formula(self):
        h=m.CellHistory();add(h)
        gp=np.array([2,1,1])/4
        sp=(np.array([1,0,0])+100*gp)/101
        b0=(np.array([1,0,0])+30*sp)/31
        np.testing.assert_allclose(h.b0("Hard","deuce"),b0)
        p1=(np.array([1,0,0])+50*b0)/51
        p2=(np.array([1,0,0])+50*p1)/51
        got,count,matches=h.tendency("A","server","Hard","deuce","20230124",None,50)
        np.testing.assert_allclose(got,p2);self.assertEqual(count,1);self.assertEqual(matches,1)

    def test_decay_uses_source_age_not_embargo_age(self):
        h=m.CellHistory();add(h,day="20200101",analysis="20201231")
        _,count,_=h.tendency("A","server","Hard","deuce","20201231",365,50)
        self.assertAlmostEqual(count,.5)

    def test_both_actor_roles_and_unique_match_support(self):
        h=m.CellHistory()
        obs=[(raw("20230101"),0),(raw("20230101"),1),(raw("20230101",server="B",returner="A"),2)]
        h.ingest("match","20230101",obs,"20230124")
        self.assertEqual(h.match_counts[("server","A")],1)
        self.assertEqual(h.raw_counts[("server","A")],2)
        self.assertEqual(h.raw_counts[("returner","A")],1)
        a=h.features(raw(),"A1")[0]
        b=h.features(raw(server="A",returner="unseen"),"A1")[0]
        np.testing.assert_allclose(a[11:14],b[11:14]);self.assertFalse(np.array_equal(a[14:17],b[14:17]))

    def test_same_date_match_order_invariance(self):
        h1,h2=m.CellHistory(),m.CellHistory()
        for h,order in ((h1,(0,2)),(h2,(2,0))):
            for target in order:add(h,match=str(target),target=target)
        for one,two in zip(h1.features(raw(),"A1")[:3],h2.features(raw(),"A1")[:3]):np.testing.assert_allclose(one,two)

    def test_future_outcome_and_suffix_mutations_do_not_change_features(self):
        h=m.CellHistory();add(h)
        before=h.features(raw(),"A1")
        mutated=raw(PtWinner="2",target="T",Notes="future illness",rally_suffix="666",final_score="6-0",eligible=False)
        after=h.features(mutated,"A1")
        for one,two in zip(before[:3],after[:3]):np.testing.assert_array_equal(one,two)
        # Removal/change of an unadmitted future match cannot enter the history API.
        for target in (0,2):
            with self.assertRaises(ValueError):add(h,day="20230125",analysis="20230124",match="future",target=target)
        np.testing.assert_array_equal(before[2],h.features(raw(),"A1")[2])

    def test_a2_only_sees_first_completed_fault(self):
        h=m.CellHistory();a=raw();b=raw(first_fault_direction=None,first_fault_direction_status="omitted",first_fault_type="wide")
        np.testing.assert_array_equal(h.features(a,"A1")[1],h.features(b,"A1")[1])
        self.assertFalse(np.array_equal(h.features(a,"A2")[1],h.features(b,"A2")[1]))

    def test_tiebreak_structural_zero_and_na_score(self):
        h=m.CellHistory();nums,cats,*_=h.features(raw(),"A1")
        np.testing.assert_array_equal(nums[6:8],[0,0])
        nums,cats,*_=h.features(raw(current_tiebreak=True,server_points="12",returner_points="10"),"A1")
        np.testing.assert_array_equal(nums[6:8],[12,10]);np.testing.assert_array_equal(cats[-2:],[5,5])

    def test_nonfinite_and_unknown_categories_fail(self):
        for kw in ({"server_games":float("nan")},{"surface":"Carpet"},{"server_hand":"?"}):
            with self.assertRaises(ValueError):m.CellHistory().features(raw(**kw),"A1")

    def test_no_identity_or_date_predictor(self):
        names=set(m.NUMERIC_NAMES)|set(m.category_map("A2"))
        self.assertFalse(names.intersection({"server","returner","date","match_date","Notes","PtWinner","target"}))
        self.assertLess(len(names),35)


class PreprocessingAndSelectionTests(unittest.TestCase):
    def arrays(self):
        numeric=np.arange(4*len(m.NUMERIC_NAMES),dtype=np.float64).reshape(4,-1)
        categorical=np.zeros((4,len(m.category_map("A1"))),dtype=np.int32)
        return numeric,categorical

    def test_training_scaler_never_refits_on_later_rows(self):
        x,c=self.arrays();pre=m.Preprocessor("A1").fit(x,c,stage="train")
        before=copy.deepcopy(pre.manifest());later=x+1e9
        out=pre.transform(later,c,family="L")
        self.assertTrue(sparse.issparse(out));self.assertEqual(out.dtype,np.float64);self.assertEqual(before,pre.manifest())
        with self.assertRaises(ValueError):pre.fit(later,c,stage="selection")
        with self.assertRaises(ValueError):m.Preprocessor("A1").fit(x,c,stage="calibration")
        self.assertEqual(pre.transform(x,c,family="N").shape[1],len(m.NUMERIC_NAMES)+len(c[0]))

    def test_saved_fixed_vocab_and_no_imputation(self):
        x,c=self.arrays();pre=m.Preprocessor("A1").fit(x,c,stage="train")
        self.assertEqual(pre.manifest()["categories"]["server_hand"],("R","L","U"))
        x[0,0]=np.nan
        with self.assertRaises(ValueError):pre.transform(x,c,family="L")

    def test_exact_estimator_configs_without_fitting(self):
        l=m.make_estimator("L",.1);self.assertEqual(l.solver,"saga");self.assertEqual(l.max_iter,300)
        self.assertEqual(m.make_estimator("L",.1,retry=True).max_iter,1000)
        n=m.make_estimator("N",15);self.assertEqual(n.max_iter,120);self.assertEqual(n.min_samples_leaf,200)
        self.assertEqual(m.make_estimator("N",15,probe=True).max_iter,20)
        self.assertFalse(n.early_stopping);self.assertEqual(n.max_bins,63)
        with self.assertRaises(ValueError):m.make_estimator("L",100)

    def test_prespecified_tie_rules_not_transitive(self):
        self.assertEqual(m.choose_candidate({0:1.,1:1.001,2:1.0008,3:1.0019},"B1"),3)
        self.assertEqual(m.choose_candidate({.1:1.003,1.:1.0015,10.:1.},"L"),1.)
        self.assertEqual(m.choose_candidate({15:1.0019,31:1.},"N"),15)
        self.assertEqual(m.designate({"B0":1.003,"B1":1.0015,"L":1.,"N":.9999}),"B1")

    def test_support_limits(self):
        y=np.repeat(np.arange(3),1000);matches=[str(i%50) for i in range(3000)]
        self.assertTrue(m.support(y,matches,"train")["sufficient"])
        self.assertTrue(m.support(y,matches,"calibration")["sufficient"])
        self.assertFalse(m.support(y[:-1],matches[:-1],"calibration")["sufficient"])
        self.assertFalse(m.support(y,["one"]*3000,"selection")["sufficient"])

    def test_calibration_fixed_identity_and_probability_validity(self):
        p=np.array([[0.,.2,.8],[.2,.3,.5]])
        np.testing.assert_allclose(m.temperature_probabilities(p,1),m.normalize_probabilities(p))
        np.testing.assert_allclose(m.temperature_probabilities(p,2).sum(axis=1),[1,1])
        self.assertEqual(m.EPSILON,1e-12)
        with self.assertRaises(ValueError):m.normalize_probabilities(np.array([[.1,.1,.1]]))


class GuardAndBudgetTests(unittest.TestCase):
    def test_ledger_one_probe_and_convergence_only_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=m.AttemptLedger(Path(directory)/"attempts.json")
            with ledger.attempt("A1_m","probe",15):pass
            with self.assertRaises(RuntimeError):ledger._check("A1_m","probe",15,False)
            with ledger.attempt("A1_m","L",.1) as record:record["status"]="convergence_warning"
            with ledger.attempt("A1_m","L",.1,retry=True):pass
            with self.assertRaises(RuntimeError):ledger._check("A1_m","L",.1,True)
            with ledger.attempt("A2_w","L",1.):pass
            with self.assertRaises(RuntimeError):ledger._check("A2_w","L",1.,True)
            with self.assertRaises(RuntimeError):ledger._check("A1_w","probe",15,False)
            self.assertEqual(len(json.loads(ledger.path.read_text())),4)

    def test_49_ceiling_and_interrupted_attempt_count(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=m.AttemptLedger(Path(directory)/"attempts.json")
            ledger.records=[{"status":"started"}]*49
            with self.assertRaises(RuntimeError):ledger._check("A1_m","L",.1,False)

    def test_exact_full_optimizer_ceiling_and_nontransferable_slots(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=m.AttemptLedger(Path(directory)/"attempts.json")
            with ledger.attempt("A1_m","probe",15):pass
            for cell in m.CELLS:
                name=m.cell_name(cell)
                for c in m.L_GRID:
                    with ledger.attempt(name,"L",c) as record:record["status"]="convergence_warning"
                    with ledger.attempt(name,"L",c,retry=True):pass
                for leaves in m.N_GRID:
                    with ledger.attempt(name,"N",leaves):pass
                for family in ("B0","B1","L","N"):
                    with ledger.attempt(name,"temperature",family):pass
            self.assertEqual(len(ledger.records),49)
            with self.assertRaises(RuntimeError):ledger._check("A1_m","L",.1,True)

    def test_nonlinear_fit_requires_successful_probe_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=m.AttemptLedger(Path(directory)/"attempts.json")
            with patch.object(m,"make_estimator") as constructor:
                with self.assertRaises(PermissionError):m.fit_candidate(directory,ledger,("A1","m"),"N",15,np.zeros((3,2)),np.array([0,1,2]))
                constructor.assert_not_called()

    def test_fit_is_denied_before_estimator_fit(self):
        with tempfile.TemporaryDirectory() as directory:
            model=MagicMock();ledger=m.AttemptLedger(Path(directory)/"attempts.json")
            with patch.object(m,"make_estimator",return_value=model),patch("experiments.tactical.gates.record_operation",side_effect=PermissionError("closed")):
                with self.assertRaises(PermissionError):m.fit_candidate(directory,ledger,("A1","m"),"L",.1,np.zeros((3,2)),np.array([0,1,2]))
            model.fit.assert_not_called();self.assertEqual(ledger.records,[])

    def test_source_firewall_runs_before_payload_read(self):
        source=m.SourceReader.__new__(m.SourceReader)
        source.permit=m.ReadPermit("development");source.matches={("m","future"):{"Date":"20250101"}}
        source.db=MagicMock()
        with self.assertRaises(PermissionError):source.read_match(("m","future"),purpose="parameter")
        source.db.execute.assert_not_called()

    def test_future_cached_labels_denied_before_any_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"artifacts/tactical/tennis/rows/evaluation/A1_m"
            with patch("experiments.tactical.gates.require_stage",side_effect=PermissionError("evaluation closed")):
                with self.assertRaises(PermissionError):m.Dataset(path,root=directory,stage="evaluation")
            with self.assertRaises(PermissionError):m.Dataset(path,root=directory,stage="train")

    def test_public_develop_evaluate_closed_before_data(self):
        with tempfile.TemporaryDirectory() as directory,patch("experiments.tactical.gates.require_stage",side_effect=PermissionError("closed")),patch.object(m,"build_rows") as loader:
            with self.assertRaises(PermissionError):m.develop(directory)
            with self.assertRaises(PermissionError):m.evaluate(directory,as_of="20260122")
            loader.assert_not_called()

    def test_deterministic_compressed_rows_and_digests(self):
        with tempfile.TemporaryDirectory() as directory:
            result=[]
            for name in ("one","two"):
                writer=m.DatasetWriter(Path(directory)/name,"A1")
                n,c,b,a=m.CellHistory().features(raw(),"A1")
                writer.append(n,c,b,0,{"row_id":["m","match",1,"A1"]})
                result.append(writer.close())
            self.assertEqual(result[0],result[1])


if __name__=="__main__":unittest.main()
