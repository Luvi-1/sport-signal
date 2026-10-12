"""Pure scoring helpers; no fitting, data loading or test unlocking.

Binary Brier uses the positive-class squared error. Multiclass Brier uses the
sum across classes. These conventions are deliberately not numerically pooled.
"""
from __future__ import annotations
import numpy as np

EPSILON = 1e-12


def validate_probabilities(y, probabilities):
    y = np.asarray(y)
    p = np.asarray(probabilities, dtype=np.float64)
    if y.ndim != 1 or not len(y) or not np.issubdtype(y.dtype, np.integer):
        raise ValueError("Labels must be a nonempty integer vector")
    if p.ndim == 1:
        p = np.column_stack((1-p, p))
    if p.ndim != 2 or p.shape[0] != len(y) or p.shape[1] < 2:
        raise ValueError("Probability shape disagrees with labels")
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("Invalid probability")
    if not np.allclose(p.sum(axis=1), 1, rtol=0, atol=1e-10):
        raise ValueError("Probability rows must sum to one; no silent renormalization")
    if (y < 0).any() or (y >= p.shape[1]).any():
        raise ValueError("Class label outside declared class order")
    return y.astype(np.int64, copy=False), p


def per_case_scores(y, probabilities, *, epsilon=EPSILON):
    if not 0 < epsilon < .5:
        raise ValueError("Invalid clipping epsilon")
    y, p = validate_probabilities(y, probabilities)
    classes = p.shape[1]
    if classes == 2:
        q = np.clip(p[:,1], epsilon, 1-epsilon)
        loss = -np.where(y == 1, np.log(q), np.log1p(-q))
        brier = (p[:,1]-y)**2
    else:
        q = np.maximum(p, epsilon)
        q = q / q.sum(axis=1, keepdims=True)
        loss = -np.log(q[np.arange(len(y)), y])
        indicator = np.eye(classes)[y]
        brier = np.sum((p-indicator)**2, axis=1)
    return {"log_loss":loss, "brier":brier, "accuracy":(np.argmax(p,axis=1)==y).astype(float)}


def classification_summary(y, probabilities, *, epsilon=EPSILON, bin_edges=None):
    y,p=validate_probabilities(y, probabilities)
    scores=per_case_scores(y,p,epsilon=epsilon)
    edges=np.asarray(np.linspace(0,1,11) if bin_edges is None else bin_edges,dtype=float)
    if edges.ndim!=1 or len(edges)<2 or not np.isfinite(edges).all() or edges[0]!=0 or edges[-1]!=1 or (np.diff(edges)<=0).any():
        raise ValueError("Reliability edges must strictly partition [0,1]")
    reliability=[]
    # Protocol-supplied fixed bins. Empty bins retained, never opportunistically merged.
    for cls in range(p.shape[1]):
        bins=np.minimum(np.searchsorted(edges,p[:,cls],side="right")-1,len(edges)-2)
        for index in range(len(edges)-1):
            mask=bins==index
            reliability.append({"class":cls,"lower":float(edges[index]),"upper":float(edges[index+1]),
                                "n":int(mask.sum()),
                                "mean_probability":float(p[mask,cls].mean()) if mask.any() else None,
                                "observed_fraction":float((y[mask]==cls).mean()) if mask.any() else None})
    return {"n":len(y),"class_counts":np.bincount(y,minlength=p.shape[1]).tolist(),
            **{key:float(value.mean()) for key,value in scores.items()},
            "brier_definition":"mean positive-class squared error" if p.shape[1]==2 else "mean sum of squared class errors",
            "log_loss_units":"natural-log units per case", "log_clip_epsilon":epsilon,
            "reliability":reliability}


def paired_cluster_interval(difference, groups, *, replicates=2000, confidence=.95,
                            seed=20261011, minimum_groups=20, weighting="case"):
    """Paired percentile bootstrap of saved per-case loss differences.

    This conditional interval does not include model-selection uncertainty. A small
    group count returns group summaries without manufacturing a precise interval.
    """
    values=np.asarray(difference,dtype=np.float64)
    ids=np.asarray(groups)
    if values.ndim!=1 or not len(values) or ids.ndim!=1 or len(ids)!=len(values) or not np.isfinite(values).all():
        raise ValueError("Finite paired losses and one group per case are required")
    if any(g is None or (isinstance(g, (float, np.floating)) and not np.isfinite(g)) or (isinstance(g,str) and not g) for g in ids):
        raise ValueError("Missing cluster identity")
    if weighting not in {"case","group"} or not 0<confidence<1 or replicates<100:
        raise ValueError("Unsupported bootstrap contract")
    unique, inverse=np.unique(ids,return_inverse=True)
    counts=np.bincount(inverse).astype(float);sums=np.bincount(inverse,weights=values)
    average=sums/counts
    estimate=float(values.mean() if weighting=="case" else average.mean())
    result={"difference":estimate,"groups":len(unique),"cases":len(values),
            "weighting":weighting,"replicates":replicates,"confidence":confidence,
            "interval_method":"paired cluster percentile; numpy quantile method=linear",
            "seed":seed,"interval":None,"group_loss_differences":average.tolist()}
    if len(unique)<minimum_groups:
        result["status"]="insufficient_groups_for_declared_interval"
        return result
    rng=np.random.default_rng(seed);sample=np.empty(replicates)
    for i in range(replicates):
        selected=rng.integers(0,len(unique),len(unique))
        sample[i]=sums[selected].sum()/counts[selected].sum() if weighting=="case" else average[selected].mean()
    alpha=(1-confidence)/2
    result.update(status="computed", interval=np.quantile(sample,[alpha,1-alpha],method="linear").tolist())
    return result
