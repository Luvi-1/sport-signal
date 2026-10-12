"""Prespecified CPU baselines and challengers for the separate V2 experiment."""
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import poisson,skellam
from sklearn.ensemble import ExtraTreesClassifier,RandomForestClassifier,HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression,PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler,OneHotEncoder
from scipy.sparse import hstack
from sportslab.evaluate import make_model as make_v1_model,SEED
from sportslab.features import FEATURES as V1_FEATURES
from experiments.v2.features import FEATURES,RATING_FEATURES

CONFIGS=[{'name':'rating_logistic','family':'rating','C':1.0}]
CONFIGS += [{'name':f'logistic_C{c}','family':'logistic','C':c} for c in (.1,1.,10.)]
CONFIGS += [{'name':f'boost_leaves{n}','family':'boost','leaves':n,'l2':l2} for n,l2 in ((7,5.),(15,10.),(31,20.))]
CONFIGS += [{'name':f'random_forest_depth{d}','family':'random_forest','depth':d,'leaf':l} for d,l in ((6,20),(12,10))]
CONFIGS += [{'name':f'extra_trees_depth{d}','family':'extra_trees','depth':d,'leaf':l} for d,l in ((10,10),(None,20))]

class FrameClassifier:
    def __init__(self,config):
        self.config=config
        family=config['family']
        self.features=RATING_FEATURES if family=='rating' else FEATURES
        if family=='v1_recipe':
            self.features=V1_FEATURES;self.estimator=make_v1_model(config['v1_config'])
        elif family in ('rating','logistic'):
            self.estimator=make_pipeline(StandardScaler(),LogisticRegression(C=config['C'],max_iter=2000,random_state=SEED))
        elif family=='boost':
            self.estimator=HistGradientBoostingClassifier(max_iter=160,learning_rate=.05,max_leaf_nodes=config['leaves'],l2_regularization=config['l2'],min_samples_leaf=30,early_stopping=False,random_state=SEED)
        elif family in ('random_forest','extra_trees'):
            cls=RandomForestClassifier if family=='random_forest' else ExtraTreesClassifier
            self.estimator=cls(n_estimators=300,max_depth=config['depth'],min_samples_leaf=config['leaf'],max_features=.7 if family=='random_forest' else .8,n_jobs=2,random_state=SEED)
        else:raise ValueError(family)
    def fit(self,frame):
        self.estimator.fit(frame[self.features],frame.target)
        return self
    def predict_proba(self,frame):return self.estimator.predict_proba(frame[self.features])

class DixonColes:
    """Weighted team attack/defense Poisson GLM plus fitted low-score correction.

    This lightweight regularized implementation has no claim of equivalence to a
    particular published commercial package. Parameters stay frozen at train end.
    """
    def __init__(self):
        self.encoder=OneHotEncoder(handle_unknown='ignore',sparse_output=True)
        self.regressor=PoissonRegressor(alpha=.1,max_iter=1500,tol=1e-8)
    @staticmethod
    def _design(frame):
        teams=np.vstack([frame[['side_a','side_b']].to_numpy(),frame[['side_b','side_a']].to_numpy()])
        home=np.r_[1-frame.neutral.to_numpy(),np.zeros(len(frame))].reshape(-1,1)
        return teams,home
    def fit(self,frame):
        teams,home=self._design(frame)
        matrix=hstack([self.encoder.fit_transform(teams),home],format='csr')
        goals=np.r_[frame.score_a.to_numpy(),frame.score_b.to_numpy()]
        age=(frame.date.max()-frame.date).dt.days.to_numpy()
        weights=np.tile(np.exp2(-age/365),2)
        self.regressor.fit(matrix,goals,sample_weight=weights)
        la,lb=self.rates(frame)
        a,b=frame.score_a.to_numpy(),frame.score_b.to_numpy()
        def objective(rho):
            tau=np.ones(len(a))
            tau[(a==0)&(b==0)]=1-la[(a==0)&(b==0)]*lb[(a==0)&(b==0)]*rho
            tau[(a==0)&(b==1)]=1+la[(a==0)&(b==1)]*rho
            tau[(a==1)&(b==0)]=1+lb[(a==1)&(b==0)]*rho
            tau[(a==1)&(b==1)]=1-rho
            if (tau<=0).any():return 1e10
            return -float(np.average(np.log(tau),weights=weights[:len(a)]))
        result=minimize_scalar(objective,bounds=(-.1,.1),method='bounded')
        if not result.success:raise ValueError('Dixon-Coles correction fit failed')
        self.rho=float(result.x)
        return self
    def rates(self,frame):
        teams,home=self._design(frame)
        prediction=self.regressor.predict(hstack([self.encoder.transform(teams),home],format='csr'))
        return np.clip(prediction[:len(frame)],.01,12),np.clip(prediction[len(frame):],.01,12)
    def predict_proba(self,frame):
        a,b=self.rates(frame)
        away=skellam.cdf(-1,a,b);draw=skellam.pmf(0,a,b);home=1-skellam.cdf(0,a,b)
        correction=self.rho*poisson.pmf(1,a)*poisson.pmf(1,b)
        p=np.column_stack([away+correction,draw-2*correction,home+correction])
        p=np.clip(p,1e-12,1)
        return p/p.sum(axis=1,keepdims=True)

def make(config):return DixonColes() if config['family']=='dixon_coles' else FrameClassifier(config)
