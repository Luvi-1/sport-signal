"""Invented redistributable fixtures; no restricted source observations."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from experiments.tactical import soccer as s
from experiments.tactical.shot_sources import pinned_blob


def event(location=(108,40)):
    return {'id':'invented-shot','index':1,'type':{'name':'Shot'},'period':1,'timestamp':'00:01:00',
            'location':list(location),'play_pattern':{'name':'Regular Play'},
            'shot':{'type':{'name':'Open Play'},'body_part':{'name':'Right Foot'},
                    'outcome':{'name':'Goal'},'freeze_frame':[
                        {'location':[119,40],'position':{'id':1},'teammate':False},
                        {'location':[114,41],'position':{'id':3},'teammate':False},
                        {'location':[100,40],'position':{'id':5},'teammate':True}]}}


class SoccerGeometryTests(unittest.TestCase):
    def test_goalposts_and_native_units(self):
        g=s.goal_geometry([108,40]);self.assertEqual(g['distance_native'],12)
        self.assertAlmostEqual(g['goal_angular_width_rad'],2*math.atan(4/12));self.assertEqual(g['goal_bearing_rad'],0)
        mirror=s.goal_geometry([100,30]);other=s.goal_geometry([100,50])
        self.assertEqual(mirror['distance_native'],other['distance_native'])
        self.assertAlmostEqual(mirror['goal_bearing_rad'],-other['goal_bearing_rad'])
        self.assertAlmostEqual(mirror['goal_angular_width_rad'],other['goal_angular_width_rad'])

    def test_goal_line_and_post_degeneracy(self):
        self.assertAlmostEqual(s.goal_geometry([120,40])['goal_angular_width_rad'],math.pi)
        self.assertIsNone(s.goal_geometry([120,40])['goal_bearing_rad'])
        self.assertIsNone(s.goal_geometry([120,36])['goal_angular_width_rad'])
        self.assertFalse(s.in_goal_triangle([120,40],[120,40]))

    def test_triangle_is_finite_not_infinite_cone(self):
        self.assertTrue(s.in_goal_triangle([114,41],[108,40]))
        for xy in ([114,43],[107,40],[119,45],[121,40]):
            self.assertFalse(s.in_goal_triangle(xy,[108,40]))

    def test_invalid_coordinates(self):
        for xy in (None,[1],[1,2,3],[float('nan'),40],[121,40],[-1,40],[100,81],[True,40]):
            self.assertFalse(s.valid_location(xy))
            with self.assertRaises(ValueError):s.goal_geometry(xy)

    def test_outcome_future_mutation_does_not_change_context(self):
        original=event();before=s.extract_context(original);changed=deepcopy(original)
        changed['shot'].update(outcome={'name':'Blocked'},end_location=[0,80,0],statsbomb_xg=.999,key_pass_id='future')
        changed.update(goal_assist=True,shot_assist=True,future_event={'goal':True},under_pressure=True)
        self.assertEqual(before,s.extract_context(changed));self.assertNotEqual(s.extract_target(original),s.extract_target(changed))

    def test_all_misses_retained_penalties_shootout_excluded(self):
        for name in s.OUTCOMES:
            e=event();e['shot']['outcome']['name']=name
            self.assertIsNotNone(s.extract_context(e));self.assertEqual(s.extract_target(e)['goal'],int(name=='Goal'))
        e=event();e['shot']['type']['name']='Penalty';self.assertEqual(s.exclusion_reason(e),'penalty')
        e=event();e['period']=5;self.assertEqual(s.exclusion_reason(e),'shootout')

    def test_missing_unknown_targets_do_not_change_eligibility(self):
        e=event();del e['shot']['outcome'];self.assertIsNotNone(s.extract_context(e));self.assertIsNone(s.extract_target(e)['goal'])

    def test_partial_frames_and_keeper_ambiguity(self):
        e=event();r=s.extract_context(e)
        self.assertEqual(r['features']['recorded_opponent_count'],2)
        self.assertEqual(r['features']['keeper_depth_native'],1)
        self.assertFalse(r['quality']['complete_defense_established'])
        e['shot']['freeze_frame'].append(deepcopy(e['shot']['freeze_frame'][0]))
        self.assertIsNone(s.extract_context(e)['features']['keeper_depth_native'])
        e['shot']['freeze_frame']=[{'location':[None,40],'teammate':False}]
        r=s.extract_context(e);self.assertEqual(r['quality']['invalid_recorded_player_locations'],1)
        self.assertIsNone(r['features']['nearest_recorded_opponent_native'])
        e['shot'].pop('freeze_frame');r=s.extract_context(e)
        self.assertIsNone(r['features']['recorded_opponent_count']);self.assertFalse(r['quality']['freeze_frame_present'])

    def test_cohort_lock_and_plot_determinism(self):
        self.assertEqual(s.cohort_for(4,'2018-10-01'),'development')
        self.assertEqual(s.cohort_for(281,'2023-12-31'),'calibration_qa_only')
        self.assertEqual(s.cohort_for(281,'2024-01-01'),'test_qa_only')
        r=s.extract_context(event());r['cohort']='development';t={r['event_id']:s.extract_target(event())}
        self.assertEqual(s.development_plot([r],t),s.development_plot([r],t))
        r['cohort']='test_qa_only'
        with self.assertRaises(ValueError):s.summarize_development([r],t)
        with self.assertRaises(ValueError):s.development_plot([r],t)

    def test_missing_role_and_structural_invalidity_are_not_invented(self):
        e=event();e['shot']['freeze_frame']=[{'location':[115,40],'teammate':False}]
        r=s.extract_context(e);self.assertEqual(r['quality']['unknown_opponent_role_count'],1)
        self.assertEqual(r['features']['recorded_outfield_opponent_count'],0)
        self.assertEqual(r['features']['recorded_opponent_count'],1)
        e=event();e['period']=None;self.assertEqual(s.exclusion_reason(e),'invalid_period')
        e=event();e['shot']=None;self.assertEqual(s.exclusion_reason(e),'missing_shot_object')
        e=event();e['shot']['type']={};self.assertEqual(s.exclusion_reason(e),'missing_shot_type')

    def test_source_pin_and_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);cache=root/'cache';cache.mkdir();p=cache/'fixture.json';p.write_text('{}')
            blob=hashlib.sha1(b'blob 2\0{}').hexdigest()
            tree={'sha':'pinned','truncated':False,'tree':[{'path':'fixture.json','type':'blob','size':2,'sha':blob}]}
            kw=dict(tree=tree,commit='pinned',repository='official/source',cache=cache,staging=root/'stage',root=root,fetch=False)
            self.assertEqual(pinned_blob('fixture.json',**kw)[0],p)
            p.write_text('[]')
            with self.assertRaises(ValueError):pinned_blob('fixture.json',**kw)
            tree['sha']='other'
            with self.assertRaises(ValueError):pinned_blob('fixture.json',**kw)

if __name__=='__main__':unittest.main()
