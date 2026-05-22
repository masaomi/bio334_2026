---
name: popgen_segregating_sites
description: Segregating sites — SNP detection algorithm and Watterson's estimator theta_w
layer: L1
version: "1.4"
tags:
  - population-genetics
  - segregating-sites
  - snp
  - theta-w
  - teaching
  - bio334
---

# Segregating Sites: SNP Detection and Watterson's Estimator theta_w

## 1. Definition

A **segregating site** is a position in a multiple sequence alignment where at least two different nucleotides (alleles) are observed across the sampled sequences. In other words, it is a polymorphic position -- a site that "segregates" variation within the population sample.

- If all sequences have the same nucleotide at a given position, that site is **monomorphic** (non-segregating).
- If two or more distinct nucleotides appear at that position, the site is **segregating**.

The total number of segregating sites in an alignment is denoted **S**.

**Example:**

```
Seq1: A T G C A T G C A T
Seq2: A T G C A T G C A T
Seq3: A T A C A T G C A T
Seq4: A T G C A C G C A T
Seq5: A T G C A T G T A T
```

- Position 3: G and A are observed -> segregating
- Position 6: T and C are observed -> segregating
- Position 8: C and T are observed -> segregating
- All other positions: only one nucleotide -> monomorphic

Here, S = 3.

## 2. Relationship to theta: Watterson's Estimator

The number of segregating sites S is directly used to estimate the population-scaled mutation rate **theta** (= 2N*mu for haploids, or 4N*mu for diploids).

**Watterson's estimator** (Watterson 1975) is defined as:

```
theta_w = S / a_n
```

where:

```
a_n = Sum(1/i) for i = 1 to n-1
```

and **n** is the number of sequences (haplotypes) in the sample.

**Convention note**: theta (the population-scaled mutation rate) equals **2N*mu for haploid** populations or **4N*mu for diploid** populations. The BIO334 course primarily works with haploid sequences (one homoeolog per accession), so theta = 2N*mu is the relevant formula. You may see 4N*mu in textbooks — that assumes diploid individuals.

The quantity a_n is the (n-1)th harmonic number. It acts as a normalization factor because, under the standard neutral model, the expected number of segregating sites grows with sample size: the more sequences you sample, the more likely you are to catch rare variants that exist in the population. A segregating site is essentially what biologists call a **SNP** (Single Nucleotide Polymorphism) — a position where different individuals carry different alleles.

**Example calculation:**
If S = 10 and n = 6 sequences:

```
a_n = 1/1 + 1/2 + 1/3 + 1/4 + 1/5
    = 1.0 + 0.5 + 0.333 + 0.25 + 0.2
    = 2.283
theta_w = 10 / 2.283 = 4.38
```

To obtain a per-site estimate, divide by alignment length L:

```
theta_w_per_site = theta_w / L
```

## 3. Algorithm: Detecting Segregating Sites

1. Read all sequences from the alignment (all must be the same length).
2. For each position (column) in the alignment:
   a. Collect the nucleotides from all sequences at that position.
   b. Place them into a **set** (which removes duplicates).
   c. If the set contains more than one element, the site is segregating.
3. Increment the count S for each segregating site.

**Pseudocode:**

```
S = 0
for each position j in range(alignment_length):
    nucleotides_at_j = set()
    for each sequence in alignment:
        nucleotides_at_j.add(sequence[j])
    if len(nucleotides_at_j) > 1:
        S += 1
return S
```

**Key implementation notes:**
- Gap characters ('-') and ambiguous bases ('N') should typically be excluded or handled explicitly.
- Using a Python `set()` is the natural and efficient way to check for uniqueness at each position.
- Time complexity is O(n * L).

## 4. Connection to pi and Tajima's D

Both theta_w and pi estimate the same parameter (theta = 2N*mu for haploids, 4N*mu for diploids) under the standard neutral model, but they weight the data differently:

| Property | theta_w (Watterson) | pi (nucleotide diversity) |
|---|---|---|
| Based on | Number of segregating sites S | Average pairwise differences |
| Sensitivity | Counts each segregating site equally regardless of frequency; excess rare variants inflate theta_w relative to pi | Weighted by allele frequency; intermediate-frequency variants contribute more |
| Under neutrality | E[theta_w] = theta | E[pi] = theta |

**Tajima's D** exploits the difference between these two estimators:

```
D = (pi - theta_w) / sqrt(Var(pi - theta_w))
```

- D approx 0: Consistent with neutrality
- D < 0: Excess of rare variants -> purifying selection or population expansion
- D > 0: Excess of intermediate-frequency variants -> balancing selection or population contraction

## 5. Teaching Checkpoints

**Checkpoint 1:** If you have 10 sequences and observe S = 20 segregating sites across 1000 aligned positions, what is the per-site Watterson's estimate theta_w? Walk through the calculation of a_n step by step.

*Expected reasoning:* a_n = 1 + 1/2 + 1/3 + ... + 1/9 = 2.8289. theta_w = 20 / 2.8289 = 7.07. Per-site: 7.07 / 1000 = 0.00707.

**Checkpoint 2:** You observe that theta_w is substantially larger than pi for a gene region. What does this imply about the frequency spectrum of mutations at that locus, and what biological scenarios could explain this pattern?

*Expected reasoning:* theta_w > pi means many segregating sites but low average pairwise difference -- excess of rare variants. Tajima's D would be negative. Possible explanations include recent population expansion or purifying selection.
