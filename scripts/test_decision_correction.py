"""Header boundaries, lazy encoder calls, and frozen policy-choice regression."""
import copy
import json
import unittest
from decision_study import OUT, feasible
from decision_analysis import (choose, choose_corrected, simple_policy,
                               header_feasible, input_header, stream_reference)


class Accounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((OUT/'frozen-model.json').read_text())
        cls.records=json.loads((OUT/'corrected/heldout-t8.json').read_text())

    def rows(self, name='494_bus', words=2):
        return copy.deepcopy([r for r in self.records if r['input']==name and r['words']==words])

    def execute(self, rule, header, counters=None, constrained=True):
        calls=[]
        plans={}
        def prepare(p):
            self.assertNotIn(p, plans)
            calls.append(('prepare',p))
            plans[p]=object()
            return plans[p]
        def inspect(p, plan):
            self.assertIs(plan,plans[p])
            calls.append(('inspect',p))
            return counters[p]  # Fail if an unnecessary inspector is invoked.
        p,plan=simple_policy(rule,header,'hot',prepare,inspect,constrained)
        self.assertIs(plan,plans[p])
        return p,calls

    def test_direct_rules_never_inspect_or_prepare_a_reference(self):
        for name,words in sorted({(r['input'],r['words']) for r in self.records}):
            rs=self.rows(name,words);s=next(r for r in rs if r['policy']=='stream512')
            for constrained in (True,False):
                old,_=choose(rs,self.model,1,80,0,constrained)
                for rule in ('fixed','capacity'):
                    p,calls=self.execute(rule,input_header(s),constrained=constrained)
                    self.assertEqual(p,old[rule][0])
                    self.assertEqual(calls,[('prepare',p)])

    def test_full_exact_capacity_and_traffic_boundary(self):
        h=dict(rows=4,columns=4,nnz=4,feature_bytes=8,resident_capacity=32)
        self.assertTrue(header_feasible('full',h))
        self.assertFalse(header_feasible('full',{**h,'resident_capacity':31}))
        self.assertFalse(header_feasible('full',{**h,'nnz':3}))
        self.assertTrue(header_feasible('full',{**h,'nnz':3},False))

    def test_hot_boundary_and_empty_input(self):
        h=dict(rows=4,columns=8,nnz=4,feature_bytes=8,resident_capacity=32)
        self.assertTrue(header_feasible('hot',h))
        for z in (0,3):
            p,calls=self.execute('fixed',{**h,'nnz':z})
            self.assertEqual((p,calls),('stream512',[('prepare','stream512')]))
        self.assertTrue(header_feasible('hot',{**h,'nnz':0,'resident_capacity':0}))

    def test_unavailable_full_is_not_constructed(self):
        s=next(r for r in self.rows('1138_bus',32) if r['policy']=='stream512')
        p,calls=self.execute('capacity',input_header(s))
        self.assertEqual((p,calls),('stream512',[('prepare','stream512')]))

    def test_header_rejects_fitting_full_without_constructing_it(self):
        h=dict(rows=4,columns=4,nnz=3,feature_bytes=8,resident_capacity=32)
        self.assertEqual(self.execute('capacity',h),('stream512',[('prepare','stream512')]))

    def test_reuse_stops_at_full_without_inspection(self):
        h=input_header(next(r for r in self.rows() if r['policy']=='stream512'))
        self.assertEqual(self.execute('reuse',h),('full',[('prepare','full')]))

    def test_reuse_stops_at_hot_without_building_stream(self):
        h=dict(rows=4,columns=8,nnz=8,feature_bytes=8,resident_capacity=8)
        # Eight contributions to the retained record: 96 metadata + 8 source bytes.
        self.assertEqual(self.execute('reuse',h,{'hot':{'expected_reads':104}}),
                         ('hot',[('prepare','hot'),('inspect','hot')]))

    def test_reuse_accepts_guaranteed_hot_reuse_without_inspection(self):
        h=dict(rows=4,columns=4,nnz=2,feature_bytes=8,resident_capacity=8)
        self.assertEqual(self.execute('reuse',h),('hot',[('prepare','hot')]))

    def test_reuse_charges_rejected_hot_and_batch_before_fallback(self):
        h=dict(rows=4,columns=8,nnz=4,feature_bytes=8,resident_capacity=8)
        # Four distinct sources: only one hit, below the frozen 50% reuse threshold.
        batch=dict(expected_reads=96,expected_writes=32,stored_metadata_bytes=64)
        p,calls=self.execute('reuse',h,{'hot':{'expected_reads':96},'batch':batch})
        self.assertEqual(p,'stream512')
        self.assertEqual(calls,[('prepare','hot'),('inspect','hot'),('prepare','batch'),
                                ('inspect','batch'),('prepare','stream512')])

    def test_reuse_skips_header_rejected_retention(self):
        h=dict(rows=4,columns=8,nnz=1,feature_bytes=8,resident_capacity=64)
        batch=dict(expected_reads=48,expected_writes=32,stored_metadata_bytes=40)
        self.assertEqual(self.execute('reuse',h,{'batch':batch}),
                         ('stream512',[('prepare','batch'),('inspect','batch'),('prepare','stream512')]))

    def test_reuse_skips_hot_with_no_possible_hits(self):
        for z,c in ((0,64),(4,0)):
            h=dict(rows=4,columns=8,nnz=z,feature_bytes=8,resident_capacity=c)
            batch=dict(expected_reads=16 if z==0 else 48,expected_writes=32,stored_metadata_bytes=16)
            self.assertEqual(self.execute('reuse',h,{'batch':batch}),
                             ('batch',[('prepare','batch'),('inspect','batch')]))

    def test_reference_and_feasibility_match_retained_kernel_counters(self):
        for phase in ('calibration-t8','heldout-t8','controlled-t8'):
            for r in json.loads((OUT/'corrected'/f'{phase}.json').read_text()):
                if r['policy'] not in ('stream128','stream512','full','hot'):
                    continue
                reference=stream_reference(input_header(r))
                if r['policy'].startswith('stream'):
                    self.assertEqual(reference,{k:r[k] for k in reference})
                self.assertEqual(header_feasible(r['policy'],input_header(r)),feasible(r,reference))

    def test_simple_choices_do_not_consume_timing_information(self):
        rs=self.rows();before,_=choose_corrected(rs,self.model,16,80,0)
        for r in rs:
            r['cycles']=10**12
            r['refresh_ns']=10**12
        after,_=choose_corrected(rs,self.model,16,80,0)
        for rule in ('fixed','capacity','reuse'):
            self.assertEqual(before[rule],after[rule])

    def test_all_frozen_choices_preserved(self):
        for name,words in sorted({(r['input'],r['words']) for r in self.records}):
            rs=self.rows(name,words)
            for constrained in (True,False):
                for k in self.model['valid_uses']:
                    for bw in self.model['bandwidth_mb_s']:
                        before,_=choose(rs,self.model,k,bw,0,constrained)
                        after,_=choose_corrected(rs,self.model,k,bw,0,constrained)
                        self.assertEqual({r:v[0] for r,v in before.items()},
                                         {r:v[0] for r,v in after.items()})


if __name__=='__main__':
    unittest.main()
