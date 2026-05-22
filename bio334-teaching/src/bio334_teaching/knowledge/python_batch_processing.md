---
name: python_batch_processing
description: Batch processing — glob, os.system, and shell script patterns for bulk analysis
layer: L1
version: "1.4"
tags:
  - python
  - batch-processing
  - glob
  - shell-script
  - automation
  - teaching
  - bio334
---

# Python Batch Processing

## 1. Why Batch Processing?

Bioinformatics rarely involves analyzing a single file. A typical project has dozens or hundreds of genes, samples, or conditions -- all requiring the same analysis.

### The A. kamchatica Use Case

```
halleri/
  AT2G19010.fasta
  AT2G19150.fasta
  ...
lyrata/
  AT2G19010.fasta
  AT2G19150.fasta
  ...
```

Calculating nucleotide diversity for each file manually would be tedious and error-prone.

---

## 2. Shell Script Approach

The simplest batch processing tool:

```sh
#!/bin/sh
for f in halleri/*.fasta; do
    python calc_diversity.py "$f"
done
```

**Advantages**: Simple, independent lines, works with any command-line tool.
**Limitations**: No built-in filtering, error handling, or result collection.

---

## 3. Python Approach (Preferred)

### File Discovery with glob

```python
import glob

fasta_files = glob.glob("halleri/*.fasta")
fasta_files.sort()
```

Wildcards: `*.fasta`, `halleri/AT2G*.fasta`, `*/AT2G19010.fasta`

### Direct Import Approach

```python
import glob
import os
from bio_utils import read_fasta, nucleotide_diversity

fasta_files = glob.glob("halleri/*.fasta")
fasta_files.sort()

results = {}
for filepath in fasta_files:
    seqs = read_fasta(filepath)
    pi = nucleotide_diversity(seqs)
    gene_name = os.path.basename(filepath).replace(".fasta", "")
    results[gene_name] = pi
    print(f"{gene_name}: pi = {pi:.6f}")  # f"..." is an f-string; :.6f means 6 decimal places

average_pi = sum(results.values()) / len(results)
print(f"\nAverage diversity: {average_pi:.6f}")
```

---

## 4. Alternative: os.system / subprocess

For cases where you need to run an external script rather than importing functions directly:

```python
import os
os.system(f"python calc_diversity.py {filepath}")
```

A more robust alternative is `subprocess.run()`, which can capture output and check for errors. These approaches are useful when combining tools written in different languages, but for BIO334 the direct import approach above is simpler and preferred.

---

## 5. Pattern: Pipeline Thinking

```
Input files  ->  Processing  ->  Output results
   *.fasta          function()       *.txt / dict
```

### Scaling

| Scale | Tool |
|-------|------|
| 2-3 files | Manual commands |
| 10-50 files | Shell script or Python glob |
| 100+ files | Workflow managers (Snakemake, Nextflow) |
| 1000+ files | Cluster/cloud (SLURM, AWS Batch) |

### Functions + Batches

1. **Functions** define *what* to do with one input.
2. **Batch processing** defines *how* to apply that function to many inputs.

A well-written function makes batch processing trivial.

---

## 6. The Agentic Perspective

When instructing AI for batch analysis:

> "Run nucleotide diversity analysis on all FASTA files in the halleri directory and collect results into a summary table."

This implies: file discovery, iteration, result collection. Understanding the pattern lets you verify correctness.

---

## 7. Teaching Checkpoints

**Q1**: You have 30 FASTA files in `lyrata/`. Write a snippet using glob to find all `.fa` files, compute nucleotide_diversity() on each, and store results in a dict. What imports are needed?

*Expected*: `glob`, `read_fasta` and `nucleotide_diversity` from bio_utils module.

**Q2**: A shell script runs analysis on 5 files. You need to extend to 200 files in three directories. What approach?

*Expected*: Switch to Python with `glob.glob()` for file discovery, enabling filtering, error handling, and result aggregation.
