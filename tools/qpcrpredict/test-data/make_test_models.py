#!/usr/bin/env python3
"""Build the SYNTHETIC model bundles used by the tool tests. No patient data: twelve made-up RDML
runs (six positive, six negative) of one sample each are generated with the generic assay of
qpcrpredict and a logistic-regression bundle is trained on them. synthetic_model.pkl is the test
model; tabpfn_family_bundle.pkl is the same bundle with the family name set to a TabPFN family,
so that the license refusal of the tool can be tested without a real TabPFN model.
Run:  python make_test_models.py   (writes into the directory of this script)"""
import math, os, sys, tempfile
import joblib, pandas as pd
from qpcrpredict.rdml import write_rdml
from qpcrpredict.train import fit
from qpcrpredict.bundle import load_bundle

HERE = os.path.dirname(os.path.abspath(__file__)); NCYC = 40
def curve(ct, n=NCYC, amp=1.0):
    """Sigmoid Rn curve crossing the threshold near cycle ct; a flat baseline when ct is empty."""
    if ct == "": return [1.0] * n
    return [round(1.0 + amp / (1 + math.exp(-(c - float(ct)) * 0.8)), 4) for c in range(1, n + 1)]
def run(positive, sample):
    wells, k = [], 0
    def add(s, det, task, ct, qty=""):
        nonlocal k
        for _ in range(3):
            wells.append(dict(well=str(k), sample=s, detector=det, task=task, ct=str(ct), avg_ct="", ct_sd="", qty=str(qty), avg_qty="", qty_sd="", rn=curve(ct), drn=None)); k += 1
    for det in ("NPM1 mut A", "ABL"):
        for q, ct in ((1e5, 20.0), (1e4, 23.32), (1e3, 26.64), (1e2, 29.96)):
            add(f"STD {q:g}", det, "STANDARD", ct, q)
        add("water", det, "NTC", "")
    add(sample, "ABL", "UNKNOWN", 22.0)
    add(sample, "NPM1 mut A", "UNKNOWN", 28.0 if positive else "")
    return {"path": "synthetic", "meta": {"run_date": "2020-01-01"}, "wells": wells}

with tempfile.TemporaryDirectory() as d:
    rows = []
    for i in range(12):
        pos = i % 2 == 0; s = f"P{i}"
        write_rdml(run(pos, s), os.path.join(d, f"r{i}.rdml"), {"ABL"})
        rows.append(dict(sample=s, target="NPM1", label="positive" if pos else "negative", run_file=f"r{i}.rdml"))
    pd.DataFrame(rows).to_csv(os.path.join(d, "labels.csv"), index=False)
    out = os.path.join(HERE, "synthetic_model.pkl")
    fit(d, os.path.join(d, "labels.csv"), model_name="logreg", out=out, cv=False, assay="aml_mrd", log=lambda *a: None)
b = dict(load_bundle(os.path.join(HERE, "synthetic_model.pkl"))); b["model_name"] = "tabpfn_v26"
joblib.dump(b, os.path.join(HERE, "tabpfn_family_bundle.pkl"))
print("written synthetic_model.pkl and tabpfn_family_bundle.pkl")
