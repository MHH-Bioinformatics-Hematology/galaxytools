#!/usr/bin/env python
"""Keep the expected barcode combinations of a Cutadapt demultiplexing run.

Cutadapt's combinatorial demultiplexing mode writes one file pair per observed
combination of a forward and a reverse barcode, named after the barcodes. This
script reads a table of the sample/barcode combinations that were actually
multiplexed, and moves the corresponding file pairs into the output directory
under their sample name. Every other combination is left behind and therefore
discarded.
"""

import argparse
import os
import re
import sys

# Sample names end up as file names that Galaxy parses back into collection
# element identifiers, so restrict them to characters that survive that trip.
SAMPLE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def parse_combinations(path):
    """Return [(sample, forward_barcode, reverse_barcode)] from a table file."""
    combinations = []
    seen = set()
    with open(path) as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = [field.strip() for field in line.split("\t")]
            if fields[0].lower() == "sample":
                continue
            if len(fields) < 3 or not all(fields[:3]):
                raise ValueError(
                    "Line %d of the combinations table does not have three "
                    "non-empty tab-separated columns: %r" % (lineno, line)
                )
            sample, forward_barcode, reverse_barcode = fields[:3]
            if not SAMPLE_NAME_RE.match(sample):
                raise ValueError(
                    "Line %d: %r is not a usable sample name. Use letters, "
                    "digits, '.', '_', '+' and '-' only." % (lineno, sample)
                )
            if sample in seen:
                raise ValueError(
                    "Line %d: sample name %r is used more than once."
                    % (lineno, sample)
                )
            seen.add(sample)
            combinations.append((sample, forward_barcode, reverse_barcode))
    if not combinations:
        raise ValueError("The combinations table does not contain any samples.")
    return combinations


def has_reads(path):
    """Cutadapt creates a file for every barcode combination it can form, so an
    existing but empty file means that no read pair carried that combination."""
    return os.path.exists(path) and os.path.getsize(path) > 0


def collect(combinations, prefix, outdir):
    """Move the demultiplexed pairs of known combinations into outdir."""
    assigned = []
    missing = []
    for sample, forward_barcode, reverse_barcode in combinations:
        pair = "%s-%s" % (forward_barcode, reverse_barcode)
        source_forward = "%s%s_R1.fastq" % (prefix, pair)
        source_reverse = "%s%s_R2.fastq" % (prefix, pair)
        if has_reads(source_forward) and has_reads(source_reverse):
            os.rename(
                source_forward,
                os.path.join(outdir, "%s_forward.fastqsanger" % sample),
            )
            os.rename(
                source_reverse,
                os.path.join(outdir, "%s_reverse.fastqsanger" % sample),
            )
            assigned.append((sample, pair))
        else:
            missing.append((sample, pair))
    return assigned, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "combinations",
        help="Tabular file with the columns sample, forward MID, reverse MID",
    )
    parser.add_argument(
        "--prefix",
        default="temp_",
        help="File name prefix used for the Cutadapt output files",
    )
    parser.add_argument(
        "--outdir",
        default="outputs",
        help="Directory the per-sample files are moved into",
    )
    args = parser.parse_args()

    combinations = parse_combinations(args.combinations)
    os.makedirs(args.outdir, exist_ok=True)
    assigned, missing = collect(combinations, args.prefix, args.outdir)

    for sample, pair in assigned:
        print("%s\t%s\tassigned" % (sample, pair))
    for sample, pair in missing:
        print("%s\t%s\tno read pair carried this combination" % (sample, pair))

    if not assigned:
        raise ValueError(
            "None of the %d expected barcode combinations was found in the "
            "reads. Check that the barcode names in the combinations table "
            "match the sequence names in the MID FASTA file, and that the "
            "error tolerance is not too strict." % len(combinations)
        )
    print(
        "\n%d of %d samples were demultiplexed."
        % (len(assigned), len(combinations))
    )


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        sys.exit("Error: %s" % error)
