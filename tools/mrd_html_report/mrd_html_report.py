#!/usr/bin/env python3
"""Write a self-contained HTML report (no external resources) from the
final report table of the MRD workflow.

The table (tab separated, header line) is embedded as JSON; the page groups
the samples by PatientId (H number) and renders overview, filters and
per-sample details in the browser.
"""
import argparse
import csv
import datetime
import json
import os
import sys

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "template.html")
FILL_COLUMNS = ("PatientId", "Primer", "DNAPosition", "Transcript")


def read_tsv(path):
    with open(path, newline="") as fh:
        rows = [r for r in csv.reader(fh, delimiter="\t")
                if r and not r[0].startswith("#")]
    if not rows:
        sys.exit(f"{path}: empty table")
    # header names are matched by name in the page; stray spaces would
    # break that
    return [h.strip() for h in rows[0]], rows[1:]


def read_corrections(path):
    # CSV written by the workflow step 'Sample table corrections':
    # sample,column,"original","corrected"
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    return [r[:4] for r in rows[1:] if len(r) >= 4]


def fill_from_sample_table(header, rows, path):
    # rows the workflow lost (all NA) still get PatientId, Primer and marker
    # from the sample table
    with open(path, newline="") as fh:
        st = list(csv.DictReader(fh))
    by_sample = {r.get("Sample", "").strip(): r for r in st}
    for col in FILL_COLUMNS:
        if col not in header:
            header.append(col)
            for r in rows:
                r.append("")
    idx = {c: header.index(c) for c in ("sample",) + FILL_COLUMNS
           if c in header}
    for r in rows:
        src = by_sample.get(r[idx["sample"]].strip()) if "sample" in idx \
            else None
        if not src:
            continue
        for col in FILL_COLUMNS:
            if r[idx[col]] in ("", "NA", ".") and src.get(col, "").strip():
                r[idx[col]] = src[col].strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report",
                    help="final report table (tab separated, with header)")
    ap.add_argument("-o", "--output", required=True,
                    help="HTML file to write")
    ap.add_argument("--corrections",
                    help="sample table corrections (CSV) from the workflow")
    ap.add_argument("--sample-table",
                    help="sample table (CSV) used to fill PatientId, Primer "
                         "and marker of lost samples")
    ap.add_argument("--title", default="",
                    help="run name shown in the header, e.g. MRD2026-034")
    ap.add_argument("--workflow", default="",
                    help="workflow name and version shown in the header")
    # wet-lab verdict (information only, does not change any decision)
    ap.add_argument("--wetlab-min-mapped", type=float, default=0.5,
                    help="mapped / all reads below this: much sequencing "
                         "output was unmappable")
    ap.add_argument("--wetlab-min-on-target", type=float, default=0.5,
                    help="reads at the target site / mapped reads below "
                         "this: primers amplify off target")
    ap.add_argument("--wetlab-min-quality", type=float, default=0.5,
                    help="reads passing the quality filter / all reads "
                         "below this: low sequencing quality")
    ap.add_argument("--wetlab-min-families", type=float, default=0.1,
                    help="read families / all reads below this: few "
                         "distinct molecules")
    args = ap.parse_args()

    header, rows = read_tsv(args.report)
    width = len(header)
    rows = [(r + [""] * width)[:width] for r in rows]
    if args.sample_table:
        fill_from_sample_table(header, rows, args.sample_table)
    corrections = read_corrections(args.corrections) \
        if args.corrections else []
    data = {
        "header": header,
        "rows": rows,
        "title": " | ".join(x for x in (args.title, args.workflow) if x),
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "corrections": corrections,
        "wetlab": {"min_mapped": args.wetlab_min_mapped,
                   "min_on_target": args.wetlab_min_on_target,
                   "min_quality": args.wetlab_min_quality,
                   "min_families": args.wetlab_min_families},
    }
    # "</" must not appear inside the <script> element
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    with open(TEMPLATE) as fh:
        page = fh.read()
    if page.count("__DATA__") != 1:
        sys.exit("template: expected exactly one __DATA__ placeholder")
    with open(args.output, "w") as fh:
        fh.write(page.replace("__DATA__", payload))


if __name__ == "__main__":
    main()
