#!/usr/bin/env python3
"""Build a small, fully SYNTHETIC ABI 7500 .eds (zip) for testing the qpcrpredict Galaxy tool.

No patient data: one made-up sample 'SAMPLE1' with an NPM1 (positive) target triplicate and
an ABL reference triplicate, plus standard-curve wells so the QC R^2 is well defined.
Run:  python make_synthetic_eds.py synthetic_run.eds
"""
import sys, zipfile, math

NCYC = 40

def sigmoid_curve(ct, amp=1.0):
    # delta-Rn that crosses ~0.2*amp near cycle `ct`
    return [round(amp / (1 + math.exp(-(c - ct) * 0.8)), 4) for c in range(1, NCYC + 1)]

def flat_curve(level=0.002):
    return [round(level, 4) for _ in range(NCYC)]

HEADER = ["Well", "Sample Name", "Detector", "Task", "Ct", "Avg Ct", "Ct SD",
          "Qty", "Avg Qty", "Qty SD"]

def well(idx, sample, detector, task, ct, qty, curve):
    row = [str(idx), sample, detector, task,
           ("" if ct is None else f"{ct:.3f}"), "", "",
           ("" if qty is None else f"{qty:.3f}"), "", ""]
    lines = ["\t".join(row)]
    rn = [round(v + 1.0, 4) for v in curve]
    lines.append("\t".join(["Rn values"] + [str(v) for v in rn]))
    lines.append("\t".join(["Delta Rn values"] + [str(v) for v in curve]))
    return lines

rows = []
i = 1
# SAMPLE1 NPM1 positive triplicate (Ct ~22)
for _ in range(3):
    rows += well(i, "SAMPLE1", "NPM1 mut A", "UNKNOWN", 22.0, 1.0e5, sigmoid_curve(22)); i += 1
# SAMPLE1 ABL reference triplicate (Ct ~20)
for _ in range(3):
    rows += well(i, "SAMPLE1", "ABL", "UNKNOWN", 20.0, 5.0e4, sigmoid_curve(20)); i += 1
# NPM1 standard curve (5 points, linear Ct ~ log10 qty)
for q, ct in [(1e6, 18.0), (1e5, 21.3), (1e4, 24.6), (1e3, 27.9), (1e2, 31.2)]:
    rows += well(i, f"STD {q:.0f}", "NPM1 mut A", "STANDARD", ct, q, sigmoid_curve(ct)); i += 1
# ABL standard curve
for q, ct in [(1e6, 16.0), (1e5, 19.3), (1e4, 22.6), (1e3, 25.9), (1e2, 29.2)]:
    rows += well(i, f"STD {q:.0f}", "ABL", "STANDARD", ct, q, sigmoid_curve(ct)); i += 1
# a negative control (NTC)
rows += well(i, "NTC", "NPM1 mut A", "NTC", None, None, flat_curve()); i += 1

analysis = "\t".join(HEADER) + "\n" + "\n".join(rows) + "\n"
experiment = ("<Experiment><Name>synthetic_test</Name><Operator>test</Operator>"
              "<RunStartTime>1552300800000</RunStartTime></Experiment>")  # 2019-03-11

out = sys.argv[1] if len(sys.argv) > 1 else "synthetic_run.eds"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("apldbio/sds/analysis_result.txt", analysis)
    z.writestr("apldbio/sds/experiment.xml", experiment)
print("wrote", out)
