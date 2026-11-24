"""Regression cases for rejected/absent candidates and short-circuit accounting."""
import copy
import json
import unittest
from decision_study import OUT,feasible
from decision_analysis import choose,choose_corrected,candidate_work

class Accounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((OUT/'frozen-model.json').read_text())
        cls.records=json.loads((OUT/'heldout-t8.json').read_text())

    def rows(self,name='494_bus',words=2):
        return copy.deepcopy([r for r in type(self).records if r['input']==name and r['words']==words])

    def check_path(self,rs,rule,expected,inspected=None,constrained=True):
        decisions,_=choose_corrected(rs,self.model,1,80,0,constrained)
        work=candidate_work(rs,self.model,decisions['reuse'][0],constrained)[rule]
        inspected=expected if inspected is None else inspected
        self.assertEqual(set(work['prepare']),set(expected))
        self.assertEqual(set(work['inspect']),set(inspected))
        by={r['policy']:r for r in rs}
        self.assertEqual(decisions[rule][1],sum(by[p]['prepare_ns'] for p in expected)+sum(by[p]['inspect_ns'] for p in inspected))
        return decisions

    def test_absent_full(self):
        rs=self.rows('1138_bus',32)
        self.assertNotIn('full',{r['policy'] for r in rs})
        self.check_path(rs,'capacity',['stream512'],[])

    def test_unconstrained_direct_choices_need_no_inspection(self):
        for rule,policy in (('fixed','hot'),('capacity','full'),('reuse','full')):
            self.check_path(self.rows(),rule,[policy],[],False)

    def test_rejected_fixed_is_charged(self):
        rs=self.rows();hot=next(r for r in rs if r['policy']=='hot')
        hot['expected_reads']=10**12
        d=self.check_path(rs,'fixed',['stream512','hot'])
        self.assertEqual(d['fixed'][0],'stream512')

    def test_reuse_stops_at_full(self):
        d=self.check_path(self.rows(),'reuse',['stream512','full'])
        self.assertEqual(d['reuse'][0],'full')

    def test_reuse_stops_at_hot_after_full_rejection(self):
        rs=self.rows();by={r['policy']:r for r in rs}
        by['full']['expected_reads']=10**12
        by['hot']['expected_reads']=by['stream512']['expected_reads']-by['stream512']['nnz']*by['stream512']['feature_bytes']+by['hot']['hot_entries']*by['hot']['feature_bytes']
        d=self.check_path(rs,'reuse',['stream512','full','hot'])
        self.assertEqual(d['reuse'][0],'hot')

    def test_fallback_pays_rejected_candidates(self):
        rs=self.rows();by={r['policy']:r for r in rs}
        for p in ('full','hot','batch'):by[p]['expected_reads']=10**12
        d=self.check_path(rs,'reuse',['stream512','full','hot','batch'])
        self.assertEqual(d['reuse'][0],'stream512')

    def test_original_selections_preserved(self):
        for name,words in sorted({(r['input'],r['words']) for r in type(self).records}):
            rs=self.rows(name,words)
            for constrained in (True,False):
                before,_=choose(rs,self.model,16,80,0,constrained)
                after,_=choose_corrected(rs,self.model,16,80,0,constrained)
                self.assertEqual({k:v[0] for k,v in before.items()},{k:v[0] for k,v in after.items()})

if __name__=='__main__':unittest.main()
