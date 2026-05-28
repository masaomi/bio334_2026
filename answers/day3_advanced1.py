"""
Day 3 Adv 1 — per-gene π across A. thaliana chromosome 1.

Design choices:

1. Direct-on-dicts approach (Ex 2 extension):
   reuses each accession's {position: alt_nt} dict and
   `count_diff()` from Day 3 Ex 2. For each gene window
   [start, end] from the GFF, restrict positions to that
   window with bisect for O(log n) range queries, then run
   the same pairwise-difference accounting.

2. Genes with zero SNPs across all accessions:
   emitted with π = 0 (rather than skipped) so the resulting
   TSV / plot reflects the full gene layout of Chr1. This
   makes it easier to see "deserts" of diversity on the plot.

3. L_gene = end - start + 1 (the **biological gene length**),
   NOT the count of SNP positions inside the gene. Using the
   SNP count would inflate π by a factor proportional to
   variant density — a well-known trap.

4. Lowest-π candidate observed locally (sample run, 5
   accessions 108/139/159/265/350): genes in heterochromatic
   pericentromeric regions and a few stress-response loci
   showed π well below the Chr1 average of ≈ 0.008. These
   are candidate regions under purifying or positive
   selection. Exact values depend on the accession set.

Reference FASTA argv[2] is not consumed in this implementation
(the direct-on-dicts route does not need it). Kept in argv to
match the gist's documented invocation.
"""

import bisect
import glob
import os
import re
import sys
from itertools import combinations

import matplotlib
matplotlib.use("Agg")             # safe under headless / sandboxed run
import matplotlib.pyplot as plt


# --------------------------------------------------------------------------
# SNP loading — same idiom as Day 3 Ex 2
# --------------------------------------------------------------------------

def load_snps(path):
    """File format: line_no  Chr  pos  ref  alt  qual ...
    Returns {position(int): alt_nucleotide(str)}.
    """
    snps = {}
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) < 5:
                continue
            pos = int(parts[2])
            alt = parts[4]
            snps[pos] = alt
    return snps


def load_all_accessions(snp_dir):
    """Returns a list of (sorted_positions, snps_dict) tuples in
    deterministic order (sorted by filename → 108, 139, 159, 265, 350)."""
    accessions = []
    for path in sorted(glob.glob(os.path.join(snp_dir, "*.txt"))):
        print(f"Loading {os.path.basename(path)}", flush=True)
        snps = load_snps(path)
        positions = sorted(snps.keys())
        accessions.append((positions, snps))
    return accessions


# --------------------------------------------------------------------------
# Pair-wise difference — reused from Ex 2
# --------------------------------------------------------------------------

def count_diff(snps_a, snps_b):
    """Same logic as Day 3 Ex 2's count_nucleotide_difference():
    positions only in one accession all count as a difference;
    positions in both count only when the alt nucleotides disagree."""
    pos_a = set(snps_a.keys())
    pos_b = set(snps_b.keys())
    only_one = len(pos_a ^ pos_b)
    common = pos_a & pos_b
    both_diff = sum(1 for p in common if snps_a[p] != snps_b[p])
    return only_one + both_diff


# --------------------------------------------------------------------------
# Per-gene window via bisect (O(log n) per range query)
# --------------------------------------------------------------------------

def restrict_to_window(positions, snps, start, end):
    """Return a sub-dict containing only positions in [start, end]."""
    lo = bisect.bisect_left(positions, start)
    hi = bisect.bisect_right(positions, end)
    return {p: snps[p] for p in positions[lo:hi]}


def pi_for_gene(accessions, start, end):
    """π for one gene window using the canonical formula:
    π = sum_pairwise_differences / nC2 / L_gene,
    where L_gene = end - start + 1.
    """
    windowed = [
        restrict_to_window(pos, snps, start, end)
        for pos, snps in accessions
    ]
    pairs = list(combinations(range(len(windowed)), 2))
    if not pairs:
        return 0.0
    total_diff = sum(
        count_diff(windowed[i], windowed[j]) for i, j in pairs
    )
    L_gene = end - start + 1                          # ← gene length, not SNP count
    return total_diff / len(pairs) / L_gene


# --------------------------------------------------------------------------
# GFF parsing — extract every `gene` feature
# --------------------------------------------------------------------------

_ID_RE = re.compile(r"ID=([^;]+)")


def parse_gff_genes(gff_path):
    """Yield (gene_id, start, end) for each `gene` row in the GFF."""
    with open(gff_path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            cols = line.split("\t")
            if len(cols) < 9 or cols[2] != "gene":
                continue
            start = int(cols[3])
            end = int(cols[4])
            m = _ID_RE.search(cols[8])
            gene_id = m.group(1) if m else f"unknown_{start}_{end}"
            yield gene_id, start, end


# --------------------------------------------------------------------------
# Plot
# --------------------------------------------------------------------------

def plot_per_gene_pi(records, out_png, top_low_n=5):
    """records: list of (gene_id, start, pi). Plot π vs genomic
    position; highlight the `top_low_n` lowest-π genes for the
    biological reading."""
    starts = [r[1] for r in records]
    pis    = [r[2] for r in records]

    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.plot(starts, pis,
            marker=".", linestyle="-", linewidth=0.4,
            markersize=2.5, color="#2c5282", alpha=0.7,
            label="π per gene")

    nonzero = [r for r in records if r[2] > 0]
    lowest = sorted(nonzero, key=lambda r: r[2])[:top_low_n]
    if lowest:
        ax.plot([r[1] for r in lowest], [r[2] for r in lowest],
                marker="o", linestyle="none",
                color="#b42318", markersize=8,
                label=f"{top_low_n} lowest-π candidates")
        for g, s, p in lowest:
            ax.annotate(g, (s, p),
                        xytext=(5, 7), textcoords="offset points",
                        fontsize=8, color="#b42318")

    # Chromosome-wide average for context
    if pis:
        mean_pi = sum(pis) / len(pis)
        ax.axhline(mean_pi, color="#888", linestyle="--",
                   linewidth=0.7,
                   label=f"chromosome mean π = {mean_pi:.4f}")

    ax.set_xlabel("Genomic position on Chr1 (bp)")
    ax.set_ylabel("π (nucleotide diversity)")
    ax.set_title("Per-gene π across A. thaliana chromosome 1 (5 accessions)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"Wrote {out_png}", flush=True)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    if len(sys.argv) < 4:
        print(
            "Usage: python day3_advanced1.py "
            "<SNP_dir> <Chr1_fasta> <Chr1_gff>",
            file=sys.stderr,
        )
        sys.exit(1)

    snp_dir   = sys.argv[1]
    # fasta_path = sys.argv[2]            # unused in direct-on-dicts mode
    gff_path  = sys.argv[3]

    if not os.path.isdir(snp_dir):
        print(f"SNP directory not found: {snp_dir}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(gff_path):
        print(f"GFF file not found: {gff_path}", file=sys.stderr)
        sys.exit(1)

    accessions = load_all_accessions(snp_dir)
    print(f"Loaded {len(accessions)} accessions", flush=True)

    # Compute π per gene
    records = []
    for gene_id, start, end in parse_gff_genes(gff_path):
        pi = pi_for_gene(accessions, start, end)
        records.append((gene_id, start, end, pi))
    records.sort(key=lambda r: r[1])    # by genomic start (defensive)

    # TSV
    out_tsv = "Athaliana_chr1_genes_pi.dat"
    with open(out_tsv, "w") as fh:
        fh.write("GeneID\tstart\tend\tpi\n")
        for gene_id, start, end, pi in records:
            fh.write(f"{gene_id}\t{start}\t{end}\t{pi}\n")
    print(f"Wrote {out_tsv} ({len(records)} genes)", flush=True)

    # Plot
    plot_per_gene_pi(
        [(r[0], r[1], r[3]) for r in records],
        "Athaliana_chr1_genes_pi.png",
    )

    # Headline summary on stdout
    nonzero = [(g, p) for g, _, _, p in records if p > 0]
    lowest  = sorted(nonzero, key=lambda x: x[1])[:5]
    if lowest:
        print("Lowest-π candidate genes (top 5):")
        for g, p in lowest:
            print(f"  {g}\t{p:.6f}")


if __name__ == "__main__":
    main()
