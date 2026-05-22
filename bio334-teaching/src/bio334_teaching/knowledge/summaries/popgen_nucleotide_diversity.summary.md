# Nucleotide Diversity pi (Summary)

## Definition
Average number of nucleotide differences per site between any two randomly chosen sequences from a population.

## Formula
```
pi = Sum_{i<j} d_ij / (C(n,2) * L)
```
- n = number of sequences, L = sequence length, d_ij = pairwise differences
- C(n,2) = n(n-1)/2

## Algorithm
1. Read n aligned sequences of length L
2. Enumerate all C(n,2) unique pairs
3. Count nucleotide differences d_ij for each pair
4. pi = total_differences / (num_pairs * L)

## Neutral Expectation
E[pi] = theta = 4Ne*mu (diploid) or 2Ne*mu (haploid)

## Key Drivers
- pi UP: higher mu, larger Ne, balancing selection, admixture
- pi DOWN: selective sweep, bottleneck, purifying selection, inbreeding

## Common Mistakes
- Forgetting to divide by L (not comparable across loci)
- Double-counting pairs (both (i,j) and (j,i))
- Confusing pi with heterozygosity
- Ignoring gaps without adjusting L
- Assuming pi alone indicates selection
- Mixing up n (sequences) and 2n (diploid individuals)
