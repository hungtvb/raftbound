"""Unit tests for blueprint-to-art gate separation; no 'AI image = GLB' shortcuts."""
import copy
import unittest

from character_lab.reference_lock import validate_proportions


class BlueprintProductionTest(unittest.TestCase):
    def setUp(self):
        self.blueprint={
            'art_status':'PENDING_HUMAN_REVIEW',
            'target':{
                'min_bones':60,
                'triangle_budget':25000,
                'height_m':1.66,
                'height_tolerance_m':.025,
                'head_to_height_min':.115,
                'shoulder_to_height_max':.22,
            }
        }
        self.measure={
            'old':{'height':1.8196,'head_height_ratio':.0996,
                   'shoulder_height_ratio':.2330},
            'new':{'height':1.6600,'head_height_ratio':.1223,
                   'shoulder_height_ratio':.2146},
        }
        self.old_qa={'technical_pass':True,'bones':65,'triangles':24200}
        self.new_qa={'technical_pass':True,'bones':65,'triangles':24200}

    def check(self,blueprint=None,measure=None,old=None,new=None):
        return validate_proportions(blueprint or self.blueprint,
                                    measure or self.measure,
                                    old or self.old_qa,new or self.new_qa)

    def test_verified_a14_metrics_are_valid_but_never_art_approved(self):
        q=self.check()
        self.assertEqual(q['technical_gate'],'PASS')
        self.assertEqual(q['art_gate'],'PENDING_HUMAN_REVIEW')
        self.assertIn('BLOCKED',q['release_gate'])

    def test_unshrunk_heroic_body_fails(self):
        m=copy.deepcopy(self.measure)
        m['new']['height']=1.82
        m['new']['shoulder_height_ratio']=.237
        m['new']['head_height_ratio']=.101
        q=self.check(measure=m)
        self.assertEqual(q['technical_gate'],'FAIL')
        self.assertIn('height_not_within_blueprint',q['errors'])
        self.assertIn('shoulders_are_still_too_wide',q['errors'])
        self.assertIn('head_is_still_too_small',q['errors'])

    def test_skeleton_and_budget_are_strict_contracts(self):
        n=dict(self.new_qa,bones=17,triangles=26000)
        q=self.check(new=n)
        self.assertIn('bone_topology_changed',q['errors'])
        self.assertIn('polygon_budget_exceeded',q['errors'])

    def test_no_mechanical_script_can_claim_human_approval(self):
        b=copy.deepcopy(self.blueprint)
        b['art_status']='APPROVED_AUTOMATICALLY'
        q=self.check(blueprint=b)
        self.assertIn('cannot_self_approve_art_quality',q['errors'])


if __name__=='__main__':
    unittest.main()
