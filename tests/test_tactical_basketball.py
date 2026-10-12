"""Invented fixtures; provider rows are not packaged with these tests."""
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path
import tempfile
import unittest
from experiments.tactical import basketball as b


def shot(index=0):
    return {'id':f'invented-{index}','gameId':114243,'period':1,'startFrame':10+index,
            'startWallClock':400+40*index,'startGameClock':590.,'location':[-30.,4.],
            'distance':math.hypot(10.75,4),'shotClock':12.,'three':False,
            'shooterId':1,'closestDefId':6,'closestDefDist':3.,'offTeamId':10,'defTeamId':20,
            'outcome':False,'fouled':True}


def player(pid,xy,detected=1):
    return {'playerId':pid,'xyz':[*xy,0.],'isDetected':detected,'predError':.9}


def frame(index=0,rotation=-1):
    return {'frameIdx':10+index,'wallClock':400+40*index,'period':1,
            'homePlayers':[player(1,b.normalize_xy([-30,4],rotation))]+[player(i,[0,i]) for i in range(2,6)],
            'awayPlayers':[player(6,b.normalize_xy([-27,4],rotation))]+[player(i,[20,i]) for i in range(7,11)]}

META={'homeTeam':{'teamId':10},'awayTeam':{'teamId':20}}


class BasketballTests(unittest.TestCase):
    def test_feet_hoop_and_bearing(self):
        g=b.court_geometry([-30.75,0]);self.assertEqual(g['distance_ft'],10);self.assertEqual(g['absolute_hoop_bearing_rad'],0)
        self.assertEqual(b.court_geometry([-40.75,10])['absolute_hoop_bearing_rad'],math.pi/2)
        self.assertEqual(b.normalize_xy([30,-4],-1),[-30,4])
        self.assertIsNone(b.court_geometry([-40.75,0])['absolute_hoop_bearing_rad'])

    def test_corruption_and_clock(self):
        for xy in (None,[float('nan'),0],[101,0],[0,float('inf')],[True,4],[1,2,3]):
            self.assertFalse(b.valid_xy(xy))
        e=shot();e['shotClock']=30;r=b.extract_context(e)
        self.assertIsNone(r['features']['shot_clock_seconds']);self.assertTrue(r['event_geometry_eligible'])
        e['closestDefDist']=-1;self.assertFalse(b.extract_context(e)['event_geometry_eligible'])
        e=shot();e['location']=None;self.assertFalse(b.extract_context(e)['event_geometry_eligible'])

    def test_target_and_post_release_mutations(self):
        e=shot();before=b.extract_context(e);changed=deepcopy(e)
        changed.update(outcome=True,fouled=False,endFrame=1,endWallClock=0,endGameClock=0,
                       assisted=True,assistOpp=False,blocked=True,blockerId=999,
                       contestLevel='blocked',contested=True,shotQuality=100,seasonAggregate=999)
        self.assertEqual(before,b.extract_context(changed));self.assertNotEqual(b.extract_target(e),b.extract_target(changed))
        self.assertTrue(before['event_geometry_eligible']) # fouled miss remains a release

    def test_orientation_is_grouped_and_abstains(self):
        rows=[b.extract_context(shot(i)) for i in range(3)];frames={10+i:frame(i) for i in range(3)}
        rot=b.infer_rotations(rows,frames);key=(114243,10,1)
        self.assertEqual(rot[key]['rotation'],-1);self.assertEqual(rot[key]['decisive_votes'],3)
        frames[12]=frame(2,1)
        self.assertIsNone(b.infer_rotations(rows,frames)[key]['rotation']) # 2/3 below prespecified 80%
        self.assertIsNone(b.infer_rotations(rows[:1],frames)[key]['rotation'])

    def test_consistency_not_accuracy_and_detection_sensitivity(self):
        context=b.extract_context(shot());f=frame();q=b.release_quality(context,f,META,{'rotation':-1})
        self.assertTrue(q['raw_consistent_0p1ft']);self.assertFalse(q['physical_accuracy_established'])
        self.assertTrue(q['raw_consistent_and_directly_detected_0p1ft'])
        f['awayPlayers'][0]['isDetected']=0;q=b.release_quality(context,f,META,{'rotation':-1})
        self.assertTrue(q['raw_consistent_0p1ft']);self.assertFalse(q['raw_consistent_and_directly_detected_0p1ft'])
        f['awayPlayers'][0]['xyz'][0]+=.5;q=b.release_quality(context,f,META,{'rotation':-1})
        self.assertFalse(q['raw_consistent_0p1ft']);self.assertTrue(q['raw_consistent_1ft'])

    def test_partial_wrong_team_and_duplicate_frames(self):
        context=b.extract_context(shot());f=frame();f['awayPlayers']=[]
        q=b.release_quality(context,f,META,{'rotation':-1});self.assertFalse(q['raw_consistent_0p1ft'])
        self.assertFalse(q['release_has_10_unique_players'])
        f=frame();f['homePlayers'].append(f['awayPlayers'][0])
        self.assertFalse(b.release_quality(context,f,META,{'rotation':-1})['raw_consistent_0p1ft'])
        f=frame();f['period']=2;self.assertFalse(b.release_quality(context,f,META,{'rotation':-1})['raw_consistent_0p1ft'])
        context['named_defender_id']=2;self.assertFalse(b.release_quality(context,frame(),META,{'rotation':-1})['raw_consistent_0p1ft'])

    def test_streaming_only_requested_frames_and_future_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'f.jsonl.gz'
            def save(future):
                with gzip.open(path,'wt') as out:
                    for item in [frame(),future]:out.write(json.dumps(item)+'\n')
            future=frame(1);save(future);frames,qa=b.read_release_frames(path,{10})
            self.assertEqual(set(frames),{10});self.assertEqual(qa['tracking_frames'],2)
            future['homePlayers']=[player(999,[99,99])];save(future)
            self.assertEqual(frames,b.read_release_frames(path,{10})[0])

    def test_later_games_locked_from_distributions_and_samples(self):
        r=b.extract_context(shot());r['cohort']='development';targets={r['shot_id']:b.extract_target(shot())}
        result=b.summarize_development([r],targets)
        self.assertEqual(result['distance_ft'][0]['releases'],1)
        self.assertEqual(result['distance_ft'][0]['observed_makes'],0)
        r['game_id']=178442
        with self.assertRaises(ValueError):b.summarize_development([r],targets)
        with self.assertRaises(ValueError):b.development_plot([r],targets)

if __name__=='__main__':unittest.main()
