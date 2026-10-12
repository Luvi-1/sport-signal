"""Offline server tests use synthetic aggregate summaries, never provider rows."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from experiments.tactical import workbench as w

class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def report(self, sport='tennis', payload=None):
        p=self.root/w.REPORTS[sport];p.parent.mkdir(parents=True,exist_ok=True)
        code=self.root/f'experiments/tactical/{sport}.py';code.parent.mkdir(parents=True,exist_ok=True);code.write_text('# synthetic generator')
        report={'sport':sport,'phase':'descriptive','parser_sha256':w.sha256(code.read_bytes()),'predictive_gate':{'status':'closed','fitting_allowed':False},'counts':{'eligible':7}}
        if sport=='tennis':
            manifest=self.root/'docs/research/tennis/source_manifest.json';manifest.parent.mkdir(parents=True,exist_ok=True);manifest.write_text('{}')
            report['provenance']={'manifest_sha256':w.sha256(manifest.read_bytes())}
        if sport in {'soccer','basketball'}:
            helper=self.root/'experiments/tactical/shot_sources.py';helper.write_text('# synthetic helper')
            contract=self.root/'docs/research/TACTICAL_MEASUREMENT_CONTRACT.json';contract.parent.mkdir(parents=True,exist_ok=True);contract.write_text('{}')
            report['parser_dependencies_sha256']={f'experiments/tactical/{sport}.py':w.sha256(code.read_bytes()),'experiments/tactical/shot_sources.py':w.sha256(helper.read_bytes())}
            report['contract_sha256']=w.sha256(contract.read_bytes())
        p.write_text(json.dumps(payload or report))
        return p
    def test_exact_five_sport_catalog_without_fabrication(self):
        c=w.catalog(self.root)
        self.assertEqual({x['id'] for x in c['sports']},set(w.REPORTS))
        self.assertTrue(all(x['status']=='not_indexed' and x['predictive_status']=='awaiting_independent_final_review' for x in c['sports']))
    def test_index_checks_bytes_and_detects_mutation(self):
        p=self.report(); w.index_reports(self.root)
        self.assertEqual(w.report_status(self.root,'tennis')[0],'descriptive_available')
        p.write_text(p.read_text()+' ')
        self.assertEqual(w.report_status(self.root,'tennis'),('integrity_mismatch',None))
    def test_generator_mutation_fails_closed(self):
        self.report();w.index_reports(self.root)
        (self.root/'experiments/tactical/tennis.py').write_text('# changed')
        self.assertEqual(w.report_status(self.root,'tennis')[0],'invalid_artifact')
    def test_shared_parser_and_contract_mutations_fail_closed(self):
        for relative in ['experiments/tactical/shot_sources.py','docs/research/TACTICAL_MEASUREMENT_CONTRACT.json']:
            self.report('soccer');w.index_reports(self.root)
            (self.root/relative).write_text('changed')
            self.assertEqual(w.report_status(self.root,'soccer')[0],'invalid_artifact')
    def test_missing_source_manifest_fails_closed(self):
        self.report();w.index_reports(self.root)
        (self.root/'docs/research/tennis/source_manifest.json').unlink()
        self.assertEqual(w.report_status(self.root,'tennis')[0],'invalid_artifact')
    def test_wrong_sport_or_unapproved_phase_rejected(self):
        self.report(payload={'sport':'baseball','phase':'descriptive'})
        with self.assertRaises(ValueError):w.index_reports(self.root)
        self.report(payload={'sport':'tennis','phase':'trained'})
        with self.assertRaises(ValueError):w.index_reports(self.root)
    def test_wrong_manifest_path_fails_closed(self):
        self.report();m=w.index_reports(self.root)
        m['reports']['tennis']['path']='data/private.json'
        (self.root/w.INDEX).write_text(json.dumps(m))
        self.assertEqual(w.report_status(self.root,'tennis')[0],'invalid_artifact')
    def test_index_does_not_scan_raw_data(self):
        p=self.root/'data/private.json';p.parent.mkdir();p.write_text('secret')
        self.assertEqual(w.index_reports(self.root)['reports'],{})
    def test_nan_and_invalid_summary_rejected(self):
        self.report(payload={'counts':{'bad':float('nan')}})
        with self.assertRaises(ValueError):w.index_reports(self.root)
        self.report(payload=['not an object'])
        with self.assertRaises(ValueError):w.index_reports(self.root)
    def test_symlink_escape_rejected(self):
        outside=Path(self.tmp.name).parent/'outside-unused.json'
        p=self.root/'escape';p.symlink_to(outside)
        with self.assertRaises(ValueError):w.confined(self.root,'escape')
    def test_read_only_server_and_security_headers(self):
        self.report();w.index_reports(self.root)
        server=w.make_server(self.root,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def call(path,method='GET',headers=None):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
            c.request(method,path,headers=headers or {});r=c.getresponse();out=(r.status,dict(r.getheaders()),r.read());c.close();return out
        try:
            self.assertEqual(server.server_address[0],'127.0.0.1')
            status,headers,body=call('/api/catalog')
            self.assertEqual(status,200);self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
            self.assertEqual(headers['Cache-Control'],'no-store');self.assertNotIn('Access-Control-Allow-Origin',headers)
            self.assertEqual(call('/api/summary/tennis')[0],200)
            self.assertEqual(call('/api/summary/football')[0],409)
            self.assertEqual(call('/api/catalog',headers={'Host':'evil.example'})[0],403)
            self.assertEqual(call('/api/catalog',headers={'Origin':'https://evil.example'})[0],403)
            self.assertEqual(call('/api/catalog',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
            self.assertEqual(call('/api/catalog?file=data/private')[0],400)
            self.assertEqual(call('/data/private.json')[0],404)
            self.assertEqual(call('/api/document/../../private')[0],404)
            self.assertEqual(call('/api/summary/unknown')[0],404)
            for method in ['POST','PUT','DELETE','PATCH']:
                self.assertEqual(call('/api/catalog',method)[0],405)
            self.assertEqual(call('/')[0],200)
            self.assertEqual(call('/app.js')[0],200)
        finally:
            server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
