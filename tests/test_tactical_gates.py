"""Synthetic file/approval fixtures test gates without fitting or source labels."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.tactical import gates as g

class ResearchGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for p,body in [('docs/protocol.md','fixed protocol'),('experiments/tactical/gates.py','# fake gate fixture'),('experiments/tactical/model.py','# fake runner'),('data/source.txt','opaque source bytes')]:
            path=self.root/p;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
        self.args=(self.root,'example','docs/protocol.md',['experiments/tactical/gates.py','experiments/tactical/model.py'],['data/source.txt'])
    def tearDown(self):self.tmp.cleanup()
    def prepare(self):return g.prepare_binding(*self.args,metadata={'not_a_real_experiment':True},evaluation_cohort=('example',))
    def approve(self,binding,stage='development',**extra):
        path=self.root/g.APPROVAL_PATH;path.parent.mkdir(parents=True,exist_ok=True)
        review=self.root/'docs/review.json';review.write_text(json.dumps({'schema_version':1,
            'review_type':'tactical_numerical_binding_review','status':'cleared','tasks':{
            'example':{'binding_sha256':binding['binding_sha256'],'cleared_stages':[stage]}}}))
        doc={'schema_version':1,'tasks':{'example':{stage:{'status':'approved','binding_sha256':binding['binding_sha256'],'review_manifest_path':'docs/review.json','review_manifest_sha256':g.digest_file(review),'approved_at_utc':'2026-10-11T00:00:00+00:00',**extra}}}}
        path.write_text(json.dumps(doc))
    def test_no_binding_or_no_approval_is_closed(self):
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','development')
        self.prepare()
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','development')
    def test_preparation_is_deterministic_and_immutable(self):
        a=self.prepare();self.assertEqual(a,self.prepare())
        (self.root/'docs/protocol.md').write_text('changed')
        with self.assertRaises(PermissionError):self.prepare()
    def test_exact_stage_binding_and_source_are_required(self):
        b=self.prepare();self.approve(b)
        self.assertEqual(g.require_stage(self.root,'example','development')['stage'],'development')
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','evaluation')
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','train')
        (self.root/'data/source.txt').write_text('changed')
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','development')
    def test_code_runtime_and_manifest_tampering_are_rejected(self):
        b=self.prepare();self.approve(b)
        with patch.object(g,'runtime_fingerprint',return_value={'changed':True}):
            with self.assertRaises(PermissionError):g.require_stage(self.root,'example','development')
        (self.root/'experiments/tactical/model.py').write_text('changed')
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','development')
    def test_changed_review_record_cannot_authorize_a_fit(self):
        b=self.prepare();self.approve(b)
        (self.root/'docs/review.json').write_text('changed')
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','development')
        with self.assertRaises(PermissionError):g.record_operation(self.root,'example','development','L1',{},1)

    def test_source_only_or_wrong_binding_review_cannot_clear_numerical_stage(self):
        b=self.prepare();self.approve(b)
        review=self.root/'docs/review.json'
        for invalid in ({'schema_version':1,'scope':'source only'},
                        {'schema_version':1,'review_type':'tactical_numerical_binding_review','status':'cleared',
                         'tasks':{'example':{'binding_sha256':'different','cleared_stages':['development']}}}):
            review.write_text(json.dumps(invalid))
            p=self.root/g.APPROVAL_PATH;approval=json.loads(p.read_text())
            approval['tasks']['example']['development']['review_manifest_sha256']=g.digest_file(review)
            p.write_text(json.dumps(approval))
            with self.assertRaises(PermissionError):g.require_stage(self.root,'example','development')

    def test_expected_source_sha_and_path_confinement(self):
        with self.assertRaisesRegex(ValueError,'Expected source fingerprint mismatch'):
            g.prepare_binding(*self.args[:4],{'data/source.txt':'wrong'},evaluation_cohort=('example',))
        with self.assertRaises(ValueError):g.resolve(self.root,'../escape')
        with self.assertRaises(ValueError):g.task_dir(self.root,'../escape')
    def test_exact_cohort_is_bound_and_partial_global_freeze_fails(self):
        b=g.prepare_binding(*self.args,evaluation_cohort=('example','second'))
        global_path=self.root/g.GLOBAL_FREEZE_PATH
        global_path.write_text(json.dumps({'schema_version':1,'tasks':{'example':{}}}))
        self.approve(b,'evaluation',global_freeze_sha256=g.digest_file(global_path))
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','evaluation')
        with self.assertRaises(ValueError):g.prepare_binding(*self.args,evaluation_cohort=('second',))
        with self.assertRaises(ValueError):g.prepare_binding(*self.args,evaluation_cohort=('example','example'))
    def test_operation_cap_duplicate_and_corruption(self):
        b=self.prepare();self.approve(b)
        self.assertEqual(g.record_operation(self.root,'example','development','L1',{'C':1},2),1)
        with self.assertRaises(PermissionError):g.record_operation(self.root,'example','development','L1',{'C':1},2)
        self.assertEqual(g.record_operation(self.root,'example','development','L2',{'C':10},2),2)
        with self.assertRaises(PermissionError):g.record_operation(self.root,'example','development','L3',{'C':100},2)
        with self.assertRaises(PermissionError):g.record_operation(self.root,'example','development','L3',{'C':100},3)
        path=g.task_dir(self.root,'example')/'development_operations.jsonl'
        rows=[json.loads(x) for x in path.read_text().splitlines()];rows[0]['config']['C']=999
        path.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
        with self.assertRaises(PermissionError):g.record_operation(self.root,'example','development','L3',{'C':100},2)
    def test_evaluation_requires_all_bound_selection_files(self):
        b=self.prepare();selection=g.task_dir(self.root,'example')/'SELECTION_FREEZE.json';selection.write_text('{"done":true}')
        global_path=self.root/g.GLOBAL_FREEZE_PATH
        global_doc={'schema_version':1,'tasks':{'example':{'binding_sha256':b['binding_sha256'],'selection_path':'artifacts/tactical/example/SELECTION_FREEZE.json','selection_sha256':g.digest_file(selection)}}}
        global_path.write_text(json.dumps(global_doc));self.approve(b,'evaluation',global_freeze_sha256=g.digest_file(global_path))
        self.assertEqual(g.require_stage(self.root,'example','evaluation')['stage'],'evaluation')
        selection.write_text('changed')
        with self.assertRaises(PermissionError):g.require_stage(self.root,'example','evaluation')

if __name__=='__main__':unittest.main()
