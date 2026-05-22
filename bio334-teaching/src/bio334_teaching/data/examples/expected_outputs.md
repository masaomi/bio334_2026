# Expected Outputs for example_sequences.fa

Use these values to verify your parser and calculations.

## File Properties
- **5 sequences** (seq1-seq5), each **52 bp**
- seq5 is split across two lines (tests FASTA parser concatenation)
- seq5 has the same sequence as seq1 (0 differences)
- All positions are **1-based** in the header descriptions

## Pairwise Differences (d_ij)

| Pair | d_ij |
|------|------|
| (seq1, seq2) | 1 |
| (seq1, seq3) | 1 |
| (seq1, seq4) | 2 |
| (seq1, seq5) | 0 |
| (seq2, seq3) | 2 |
| (seq2, seq4) | 3 |
| (seq2, seq5) | 1 |
| (seq3, seq4) | 3 |
| (seq3, seq5) | 1 |
| (seq4, seq5) | 2 |

- **Total pairwise differences**: 16
- **Number of pairs**: C(5,2) = 10

## Summary Statistics

| Statistic | Value |
|-----------|-------|
| pi (per-site) | **0.030769** |
| S (segregating sites) | **4** (positions 13, 20, 25, 38) |
| theta_w (per-site) | **0.036923** |

## Verification Checklist

1. Does your parser find exactly 5 sequences?
2. Are all sequences 52 bp? (seq5 must be concatenated from two lines)
3. Does your pi calculation match 0.030769?
4. Does your segregating sites count match S = 4?
