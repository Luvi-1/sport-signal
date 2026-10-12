"""Development must not parse new-holdout outcomes before the explicit unlock."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from experiments.v2 import run

class HoldoutSealTests(unittest.TestCase):
    def test_development_reads_only_purged_history_and_is_future_invariant(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            pre=root/'data/v2/pre_holdout_development';full=root/'data/v2/processed'
            pre.mkdir(parents=True);full.mkdir(parents=True)
            row=dict(event_id='synthetic_old',date='2023-01-01',available_date='2023-01-01',season='2023',side_a='A',side_b='B',score_a=1,score_b=0,neutral=False,surface='all')
            old=pd.DataFrame([row]);old.to_csv(pre/'baseball.csv',index=False)
            future=pd.DataFrame([{**row,'event_id':'synthetic_future','date':'2025-01-01','available_date':'2025-01-01','season':'2025'}])
            pd.concat([old,future]).to_csv(full/'baseball.csv',index=False)
            original=pd.read_csv;paths=[]
            def spy(path,*a,**k):paths.append(Path(path));return original(path,*a,**k)
            with patch.object(run,'ROOT',root),patch.object(run.pd,'read_csv',side_effect=spy):
                first,_=run.features_for('baseball',development_only=True)
                future['score_a']=0;future['score_b']=1
                pd.concat([old,future]).to_csv(full/'baseball.csv',index=False)
                second,_=run.features_for('baseball',development_only=True)
            pd.testing.assert_frame_equal(first,second)
            self.assertEqual(paths,[pre/'baseball.csv',pre/'baseball.csv'])
            self.assertFalse((root/'artifacts/v2/baseball/features.csv').exists())
            self.assertTrue((root/'artifacts/v2/baseball/development_features.csv').exists())

if __name__=='__main__':unittest.main()
