---
name: bioinformatics_file_formats
description: Bioinformatics file formats — FASTA and VCF structure and parsing strategy
layer: L1
version: "1.2"
tags:
  - bioinformatics
  - fasta
  - vcf
  - file-formats
  - parsing
  - teaching
  - bio334
---

# Bioinformatics File Formats -- FASTA and VCF

> **Scope**: This file covers the **structure and rules** of FASTA and VCF formats. For Python parsing code and implementation patterns, see `python_file_io_parsing`.

## 1. Overview: Why Standard File Formats Matter

Bioinformatics depends on the exchange of data between tools, pipelines, and researchers. Standard file formats make this possible:
- Tools cannot interoperate without agreed-upon formats
- Results are not reproducible with custom formats
- Data sharing breaks down without standards

Two of the most fundamental formats in genomics are **FASTA** (for sequences) and **VCF** (for variants).

## 2. FASTA Format

### Structure

A FASTA file consists of one or more sequence records. Each record has:

1. **Header line**: Begins with `>`, followed by a sequence identifier and optional description.
2. **Sequence lines**: One or more lines of nucleotide (or amino acid) characters.

Example:
```
>sample_01
ATCGATCGATCGATCGATCG
>sample_02
ATCGATCGTTCGATCGATCG
>sample_03
ATCGATCGATCAATCGATCG
```

### Key Points

- The sequence may span **multiple lines**. Line breaks within a sequence are formatting only. A parser must concatenate all lines between one `>` header and the next.
- There is no fixed line length, though 60 or 80 characters per line is conventional.

### Common Pitfalls

- **Newline characters in sequences**: Forgetting to strip newlines results in embedded `\n` characters.
- **Extra whitespace**: Always strip whitespace when parsing.
- **Mixed case**: Normalize case before comparison.
- **Non-standard characters**: Gap characters (`-`), unknown bases (`N`), and IUPAC ambiguity codes may appear.

## 3. VCF Format (Variant Call Format)

### Purpose

VCF stores **genetic variation** -- positions where individuals differ from a reference or from each other.

### File Structure

#### Meta-information lines (prefixed with `##`)
```
##fileformat=VCFv4.3
##source=SimulatedData
```

#### Header line (prefixed with `#CHROM`)
```
#CHROM  POS  ID  REF  ALT  QUAL  FILTER  INFO  FORMAT  sample_01  sample_02  sample_03
```

#### Data lines (one per variant)
```
chr1  5   .  A  T  50  PASS  DP=30  GT  0/1  0/0  1/1
```

### Data Columns

| Column | Name | Description |
|--------|------|-------------|
| 1 | CHROM | Chromosome or contig name |
| 2 | POS | 1-based position on the chromosome |
| 3 | ID | Variant identifier (`.` if none) |
| 4 | REF | Reference allele at this position |
| 5 | ALT | Alternate allele(s), comma-separated if multiple |
| 6 | QUAL | Quality score |
| 7 | FILTER | `PASS` if variant passed filters |
| 8 | INFO | Semicolon-separated key=value pairs |
| 9 | FORMAT | Colon-separated keys for genotype fields |
| 10+ | Samples | Genotype data for each sample |

### Genotype Encoding

- **0/0**: Homozygous reference
- **0/1**: Heterozygous
- **1/1**: Homozygous alternate
- **1/2**: Heterozygous for two different ALT alleles

For haploid organisms, genotypes are single numbers: `0` or `1`.

## 4. From FASTA to VCF -- Two Representations

### FASTA: Full Sequence Representation
Every position is stored for every sample. Data scales as O(N * L).

### VCF: Variant-Only Representation
Only positions where variation exists are recorded. For low-divergence datasets, VCF is vastly more compact.

### The Connection
- FASTA stores sequences, VCF stores differences.
- Given the reference sequence and the VCF, you can reconstruct each sample's full sequence.

## 5. Parsing Strategy

### Step 1: Identify Delimiters and Structure
- FASTA: the `>` character separates records. VCF: newlines for rows, tabs for columns.

### Step 2: Plan the Data Structure
- FASTA: dictionary mapping names to sequences.
- VCF: list of dictionaries per variant, or genotype matrix.

### Step 3: Let AI Write the Parser, You Verify
Verification strategy:
- Use a small file with known correct answer
- Check edge cases: empty sequences, multiple ALT alleles, missing data
- Compare counts: number of sequences parsed should match number of `>` lines

## 6. VCF to Nucleotide Diversity -- Algorithmic Overview

Computing nucleotide diversity from a VCF file requires a different approach than from FASTA:

### Step-by-step logic

1. **Read the reference sequence** from a FASTA file to know the full sequence length L.
2. **Parse the VCF file**: for each variant line, extract POS, REF, ALT, and each sample's genotype (GT field).
3. **Reconstruct each sample's sequence**: start with the reference sequence, then apply each sample's genotype to replace bases at variant positions.
4. **Calculate pi** using the standard pairwise comparison algorithm on the reconstructed sequences.

### Alternative: Direct computation from genotypes

Instead of reconstructing full sequences, you can compute differences directly from VCF genotype data:

```
For each variant position:
    Extract alleles for all samples from GT field
    Count pairwise differences at this position
Sum all pairwise differences across all positions
Divide by (number_of_pairs * L)
```

**Key consideration**: VCF only records *variant* positions. At all non-variant positions, all samples match the reference — contributing zero differences. The sequence length L (from the reference) is still needed for normalization.

## 7. Teaching Checkpoints

### Checkpoint 1: VCF to Pi
> "You have a VCF file with 5 variant positions and a reference sequence of length 1000. Why do you need the reference sequence length to calculate pi?"

Expected: VCF only records variant sites. Non-variant positions contribute zero differences but still count toward L in the denominator. Without L, pi would be inflated.

### Checkpoint 2: FASTA Structure
> "Given a FASTA file with 10 sequences, how many lines start with `>`?"

Expected: Exactly 10.

### Checkpoint 3: VCF Interpretation
> "In a VCF file, REF=G, ALT=A, and a sample's genotype is 0/1. What are this individual's two alleles?"

Expected: One copy of G (reference, 0) and one copy of A (alternate, 1). The individual is heterozygous G/A.
