#!/usr/bin/env python3
"""Write a self-contained HTML page from the outputs of the MRD sample
sheet check: the check report (sections of problems to fix by hand), the
automatic edits per sample and the corrected sample sheet.

The page says at the top whether the sheet can be used, then gives one
card per problem type with what to do and the samples concerned, then the
automatic edits and the corrected sheet with the affected samples marked.
"""
import argparse
import csv
import datetime
import html
import io
import os
import re
import sys

SEP = re.compile(r"^-{5,}\s*$")
HERE = os.path.dirname(os.path.abspath(__file__))
GENERIC = ("Check the listed samples against the diagnostic finding "
           "and correct the sample sheet.")


def load_guide(path=os.path.join(HERE, "guide.tsv")):
    """Instructions per check: pattern, card title, what to do, label."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            pat, title, text, ok = line.rstrip("\n").split("\t")
            out.append((re.compile(pat, re.I), title, text, ok))
    return out


GUIDE = load_guide()
with open(os.path.join(HERE, "style.css"), encoding="utf-8") as _fh:
    CSS = _fh.read()


def guide(title):
    for pat, short, text, _ in GUIDE:
        if pat.search(title):
            return short, text
    return title, GENERIC


def passed_label(title):
    for pat, _, _, ok in GUIDE:
        if pat.search(title):
            return ok
    return title


def split_blocks(text):
    """Text between the dashed separator lines, as lists of lines."""
    blocks, cur = [], []
    for line in text.splitlines():
        if SEP.match(line):
            blocks.append(cur)
            cur = []
        else:
            cur.append(line)
    blocks.append(cur)
    return [[x for x in b if x.strip()] for b in blocks]


def parse_report(text):
    """Return [(title, header, rows)] for every section of the report.

    A section is a one-line title block followed by its body block;
    an empty body is written as a single '.'.
    """
    blocks = split_blocks(text)
    sections = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if len(b) != 1 or "\t" in b[0] or b[0].strip() == ".":
            i += 1
            continue
        body = blocks[i + 1] if i + 1 < len(blocks) else []
        if body and body[0].strip() == ".":
            body = []
        if body and "\t" in body[0]:
            header = body[0].split("\t")
            rows = [r.split("\t") for r in body[1:]]
        elif body:
            header, rows = ["Line"], [[r] for r in body]
        else:
            header, rows = [], []
        sections.append((b[0].strip(), header, rows))
        i += 2
    return sections


def read_edits(path):
    """Header and the rows with an edit; a tab inside an edit is kept."""
    with open(path, newline="") as fh:
        rows = [r for r in csv.reader(fh, delimiter="\t") if r]
    if not rows:
        return [], []
    rows = [r[:2] + [" ".join(x.strip() for x in r[2:])] for r in rows]
    edits = [r for r in rows[1:]
             if len(r) >= 3 and r[2].strip() not in ("", "none")]
    return rows[0], edits


def read_sheet(path):
    with open(path, newline="") as fh:
        data = fh.read()
    tab = data.count("\t") > data.count(",")
    reader = csv.reader(io.StringIO(data),
                        dialect="excel-tab" if tab else "excel")
    rows = [r for r in reader if any(x.strip() for x in r)]
    return (rows[0], rows[1:]) if rows else ([], [])


def e(s):
    return html.escape(str(s), quote=True)


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def table(header, rows, mark=None):
    out = ['<div class="tw"><table><tr>']
    out += [f"<th>{e(h)}</th>" for h in header]
    out.append("</tr>")
    for r in rows:
        cells = "".join(
            f'<td class="{"long" if len(x) > 30 else "nw"}">{e(x)}</td>'
            for x in r)
        out.append(f'<tr class="{mark(r) if mark else ""}">{cells}</tr>')
    out.append("</table></div>")
    return "".join(out)


STEPS = {
    "fail": ["Read each red card below: it says what is wrong and what "
             "to do.",
             "Correct the original sample sheet (not the corrected copy) "
             "and run the sample sheet check again.",
             "Start the MRD workflow only when this page is green or "
             "orange."],
    "warn": ["Check the automatic edits below once.",
             "Start the MRD workflow with the corrected sample sheet "
             "(it keeps the original name)."],
    "ok": ["Start the MRD workflow with this sample sheet."],
}
EDITS_TEXT = ("Nothing to fix: the check removed spaces and quotation "
              "marks, empty rows and columns, and completed obvious "
              "notation slips. Look over the changes once; the corrected "
              "sheet below already contains them.")


def verdict(problems, edits):
    if problems:
        n = sum(len(r) for _, _, r in problems)
        return "fail", (f"Fix the sample sheet by hand: "
                        f"{plural(n, 'problem')} in "
                        f"{plural(len(problems), 'check')}")
    if edits:
        return "warn", (f"Sheet can be used: {plural(len(edits), 'sample')}"
                        f" corrected automatically")
    return "ok", "Sheet can be used: no problems, no corrections"


def problem_card(title, header, rows):
    short, text = guide(title)
    unit = "sample" if header and header[0] == "Sample" else "row"
    return (f'<div class="card fail"><h2>{e(short)} '
            f'<span class="badge fail">{plural(len(rows), unit)}</span>'
            f'</h2><div class="sub">{e(title)}</div>'
            f'<div class="what"><b>What to do</b>{text}</div>'
            + table(header, rows) + "</div>")


def build(report, edits_path, sheet_path, title):
    sections = parse_report(report)[1:]
    problems = [x for x in sections if x[2]]
    passed = [t for t, _, r in sections if not r]
    eh, edits = read_edits(edits_path) if edits_path else ([], [])
    sh, sheet = read_sheet(sheet_path) if sheet_path else ([], [])
    bad = {r[0] for _, h, rows in problems if h and h[0] == "Sample"
           for r in rows if r}
    edited = {r[0] for r in edits}
    state, head = verdict(problems, edits)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    p = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, '
         'initial-scale=1">',
         f"<title>{e(title or 'Sample sheet check')}</title>",
         f"<style>{CSS}</style></head><body><main>",
         "<h1>Sample sheet check</h1>",
         f'<div class="sub">{e(title)} | {now}</div>',
         f'<div class="verdict {state}"><span class="light"></span>',
         f'<div><b>{e(head)}</b><ol class="steps">',
         "".join(f"<li>{e(s)}</li>" for s in STEPS[state]),
         "</ol></div></div>"]
    p += [problem_card(*x) for x in problems]
    if edits:
        p.append('<div class="card warn"><h2>Automatic corrections '
                 f'<span class="badge warn">{plural(len(edits), "sample")}'
                 f'</span></h2><div class="what"><b>What to do</b>'
                 f'{EDITS_TEXT}</div>' + table(eh, edits) + "</div>")
    if passed:
        p.append('<div class="card"><h2>Checks without problems '
                 f'<span class="badge ok">{len(passed)}</span></h2>'
                 '<ul class="passed">'
                 + "".join(f"<li>{e(passed_label(t))}</li>"
                           for t in passed) + "</ul></div>")
    if sh:
        si = sh.index("Sample") if "Sample" in sh else 0

        def mark(r):
            k = r[si] if si < len(r) else ""
            return "bad" if k in bad else ("edit" if k in edited else "")
        p.append(f'<div class="card"><details{" open" if problems else ""}>'
                 f"<summary>Corrected sample sheet "
                 f"({plural(len(sheet), 'sample')})</summary>"
                 '<p class="sub">red: sample with a problem to fix by hand; '
                 "orange: corrected automatically.</p>"
                 + table(sh, sheet, mark) + "</details></div>")
    p.append('<div class="foot">Generated by the MRD sample sheet check '
             "(mrd_samplesheet_report). The file contains all data and "
             "needs no internet connection.</div></main></body></html>")
    return "".join(p), state


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("report", help="check report (text)")
    ap.add_argument("--edits", help="automatic edits per sample (tabular)")
    ap.add_argument("--sheet", help="corrected sample sheet (CSV)")
    ap.add_argument("--title", default="", help="run name for the header")
    ap.add_argument("--output", required=True)
    ap.add_argument("--state", help="write ok, warn or fail to this file")
    a = ap.parse_args(argv)
    with open(a.report, encoding="utf-8", errors="replace") as fh:
        page, state = build(fh.read(), a.edits, a.sheet, a.title)
    with open(a.output, "w", encoding="utf-8") as fh:
        fh.write(page)
    if a.state:
        with open(a.state, "w") as fh:
            fh.write(state + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
