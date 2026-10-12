"""Entire training/inference path on explicitly synthetic fixtures, never research evidence."""
import os
os.environ.setdefault("OMP_NUM_THREADS","1")
os.environ.setdefault("MPLCONFIGDIR","/tmp/sportslab-test-matplotlib")
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from sportslab.data import validate_events
from sportslab.evaluate import train_evaluate,split_frames
from sportslab.features import build_features
from sportslab.cli import predict

class TrainingSmokeTest(unittest.TestCase):
    def test_train_calibrate_save_load_and_predict(self):
        records=[]
        for i,date in enumerate(pd.date_range("2016-01-01","2024-12-30",freq="2D")):
            records.append(dict(event_id=f"synthetic_{i}",date=date,available_date=date,season=str(date.year),
                side_a=f"T{i%8}",side_b=f"T{(i+1+i//8)%8}" if (i+1+i//8)%8!=i%8 else f"T{(i+1)%8}",
                score_a=1 if i%5 in (0,1,2) else 0,score_b=0 if i%5 in (0,1,2) else 1))
        data=validate_events(pd.DataFrame(records),"baseball")
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/"data"/"processed").mkdir(parents=True)
            data.to_csv(root/"data"/"processed"/"baseball.csv",index=False)
            report=train_evaluate(data,"baseball",root)
            self.assertEqual(len(report["backtests"]),5)
            self.assertTrue((root/"reports"/"baseball"/"reliability.svg").exists())
            result=predict(root,"baseball","T0","T1","2025-02-01")
            self.assertAlmostEqual(sum(result["probabilities"].values()),1)
            with self.assertRaisesRegex(ValueError,"calibration cutoff"):
                predict(root,"baseball","T0","T1","2020-01-01")
            with self.assertRaisesRegex(ValueError,"Unknown participant"):
                predict(root,"baseball","UNKNOWN","T1","2025-01-01")
    def test_partition_embargo_and_disjointness(self):
        frame=pd.DataFrame({"date":pd.date_range("2019-01-01","2024-12-31",freq="D")})
        frame["available_date"]=frame.date+pd.Timedelta(days=21)
        frame["target"]=np.arange(len(frame))%2
        train,val,test=split_frames(frame,"tennis")
        self.assertTrue((train.available_date<pd.Timestamp("2022-01-01")).all())
        self.assertTrue((val.available_date<pd.Timestamp("2023-01-01")).all())
        self.assertEqual(set(train.index)&set(val.index),set())
        self.assertEqual(set(val.index)&set(test.index),set())

if __name__=="__main__":unittest.main()
