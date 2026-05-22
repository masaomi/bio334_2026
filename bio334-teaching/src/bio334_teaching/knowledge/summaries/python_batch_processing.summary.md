# Batch Processing (Summary)

## Purpose
Apply identical analysis to multiple input files automatically.

## Three Approaches

### 1. Shell Script
```sh
for f in halleri/*.fa; do python calc.py "$f"; done
```
Simple but limited (no filtering, no result collection).

### 2. Python glob + os.system
```python
import glob, os
for f in glob.glob("halleri/*.fa"):
    os.system(f"python calc.py {f}")
```
More control, but still spawns external processes.

### 3. Direct Import (Preferred)
```python
import glob
from bio_utils import read_fasta, nucleotide_diversity
results = {}
for f in glob.glob("halleri/*.fa"):
    seqs = read_fasta(f)
    results[f] = nucleotide_diversity(seqs)
```
Cleanest: everything in Python, results as dict.

## glob Wildcards
- `*.fa` -- all FASTA files
- `halleri/gene*_H.fa` -- halleri homoeologs
- `*/gene001_*.fa` -- one gene across directories

## Pipeline Thinking
- Functions define WHAT to do with one input
- Batch processing defines HOW to apply to many inputs
- Scale: manual (2-3) -> glob (10-50) -> Snakemake (100+) -> cluster (1000+)

## Common Mistakes
- Not sorting glob results (non-reproducible order)
- Not handling empty/malformed files
- Using os.system when direct import is available
