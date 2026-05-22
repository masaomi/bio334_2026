---
name: popgen_nucleotide_diversity
description: Nucleotide diversity (pi) — definition, mathematics, algorithm, biological meaning, and teaching checkpoints
layer: L1
version: "1.2"
tags:
  - population-genetics
  - nucleotide-diversity
  - pi
  - teaching
  - bio334
---

# Nucleotide Diversity (pi)

## 1. Biological Meaning

Nucleotide diversity (pi) is the average number of nucleotide differences per site between any two randomly chosen sequences from a population. It is one of the most fundamental summary statistics in population genetics.

**Why does it matter?**

- **Measures genetic variation**: pi captures how much DNA-level diversity exists within a population. A high pi means individuals tend to differ at many sites; a low pi means the population is genetically uniform.
- **Reflects evolutionary history**: Populations that have experienced bottlenecks, selective sweeps, or recent expansions leave signatures in pi. It is a window into the demographic and selective forces shaping a population.
- **Enables comparison**: Because pi is normalized per site, you can compare diversity across genes, genomic regions, or species -- even when sequence lengths differ.
- **Connects to theory**: Under the neutral model, the expected value of pi equals 4Ne*mu (for diploids) or 2Ne*mu (for haploids), where Ne is the effective population size and mu is the per-site mutation rate. This connects an observable quantity to fundamental population parameters.

**Intuitive analogy**: Imagine picking two people at random from a crowd and reading their genomes side by side. pi tells you, on average, what fraction of positions will differ. For humans, pi is approximately 0.001, meaning roughly 1 in 1,000 bases differ between two random individuals.

---

## 2. Mathematical Definition

### Primary Formula

```
pi = (2 / (n(n-1))) * Sum_{i<j} (d_ij / L)
```

Where:
- **n** = number of sequences in the sample
- **d_ij** = number of nucleotide differences between sequence i and sequence j
- **L** = length of the aligned sequences (number of comparable sites)
- **n(n-1)/2** = total number of unique pairwise comparisons (combinations of 2 from n)

### Equivalent Plain-Language Formula

```
pi = sum of pairwise differences / (number of pairs * sequence length)
```

### Important Notes on the Formula

- The factor 2 / n(n-1) is the same as 1 / C(n,2) -- it averages over all unique pairs.
- Dividing by L normalizes per site, making pi a per-site measure (dimensionless, typically between 0 and 1).
- Without the division by L, you would have the average number of pairwise differences (sometimes called k-hat), which is useful but not comparable across loci of different lengths.

---

## 3. Step-by-step Algorithm

### Step 1: Read and Align Sequences
- Input: a set of n aligned DNA sequences of length L.
- Ensure all sequences are the same length (aligned). Handle or exclude gaps as appropriate.

### Step 2: Enumerate All Unique Pairs
- Generate all C(n, 2) = n(n-1)/2 unique pairs (i, j) where i < j.
- For n = 4 sequences, this gives 6 pairs.

### Step 3: Count Differences for Each Pair
- For each pair (i, j), walk along the alignment position by position (site = 1 to L).
- At each site, compare the nucleotides. If they differ, increment d_ij by 1.
- Record d_ij for each pair.

### Step 4: Sum and Normalize
- Compute the total: total_diff = Sum(d_ij) (sum over all pairs).
- Compute pi = total_diff / (C(n,2) * L).

**Note**: We use `total_diff` (not `S`) for the sum of pairwise differences. The symbol `S` is reserved for the number of segregating sites — a different quantity (see `popgen_segregating_sites`).

### Pseudocode

```
function compute_pi(sequences):
    n = length(sequences)
    L = length(sequences[0])
    total_diff = 0

    for i in 0 to n-2:
        for j in i+1 to n-1:
            diff = 0
            for site in 0 to L-1:
                if sequences[i][site] != sequences[j][site]:
                    diff += 1
            total_diff += diff

    num_pairs = n * (n - 1) / 2
    pi = total_diff / (num_pairs * L)
    return pi
```

---

## 4. Worked Example

### Input: 4 sequences of length 10

```
Seq1: A T G C C T A G C T
Seq2: A T G C C T A G C A
Seq3: A T G T C T A G C T
Seq4: A C G C C T A G C A
```

### Step 2: Enumerate pairs (6 pairs)

| Pair     | Sequences compared |
|----------|--------------------|
| (1, 2)   | Seq1 vs Seq2       |
| (1, 3)   | Seq1 vs Seq3       |
| (1, 4)   | Seq1 vs Seq4       |
| (2, 3)   | Seq2 vs Seq3       |
| (2, 4)   | Seq2 vs Seq4       |
| (3, 4)   | Seq3 vs Seq4       |

### Step 3: Count differences

- **(1, 2)**: site 10 differs (T vs A) -> d = **1**
- **(1, 3)**: site 4 differs (C vs T) -> d = **1**
- **(1, 4)**: site 2 differs (T vs C), site 10 differs (T vs A) -> d = **2**
- **(2, 3)**: site 4 differs (C vs T), site 10 differs (A vs T) -> d = **2**
- **(2, 4)**: site 2 differs (T vs C) -> d = **1**
- **(3, 4)**: site 2 differs (T vs C), site 4 differs (T vs C), site 10 differs (T vs A) -> d = **3**

### Step 4: Compute pi

- Total differences: total_diff = 1 + 1 + 2 + 2 + 1 + 3 = **10**
- Number of pairs: C(4, 2) = **6**
- Sequence length: L = **10**

```
pi = 10 / (6 * 10) = 10 / 60 = 0.1667
```

**Interpretation**: On average, about 16.7% of sites differ between any two randomly chosen sequences in this sample.

---

## 5. Key Intuitions -- What Drives pi

### What makes pi go UP?

| Factor | Mechanism |
|--------|-----------|
| Higher mutation rate (mu) | More mutations introduced per generation -> more differences accumulate |
| Larger effective population size (Ne) | More lineages maintained -> longer coalescence times -> more mutations between them |
| Balancing selection | Maintains multiple alleles at intermediate frequencies -> inflates local pi |
| Population structure / admixture | Mixing of divergent subpopulations can raise pi |

### What makes pi go DOWN?

| Factor | Mechanism |
|--------|-----------|
| Positive (directional) selection / selective sweep | Beneficial allele drags nearby variants to fixation -> reduces pi around the selected site |
| Population bottleneck | Drastic reduction in Ne -> loss of lineages -> fewer pairwise differences |
| Purifying selection | Deleterious mutations removed -> functional regions have lower pi than neutral ones |
| Recent population expansion from few founders | Low initial diversity, not yet recovered |
| Inbreeding | Reduces heterozygosity and, in a population sample, can reduce pi |

### The Neutral Expectation

Under neutrality: E[pi] = theta = 4Ne*mu (diploid) or 2Ne*mu (haploid).

This is the key link: pi is a direct estimator of the population-scaled mutation rate theta. When observed pi deviates from expectations, it signals non-neutral evolution or demographic events.

---

## 6. Connection to Tajima's D

Tajima's D compares two estimators of theta:

| Estimator | Symbol | Based on | Sensitive to |
|-----------|--------|----------|-------------|
| Nucleotide diversity | pi (= theta_pi) | Average pairwise differences | Intermediate-frequency variants |
| Watterson's estimator | theta_W | Number of segregating sites (S) | Total number of variable sites regardless of frequency |

- **D approx 0**: pi approx theta_W -> consistent with neutral evolution.
- **D < 0**: pi < theta_W -> excess of rare variants. Suggests recent population expansion or purifying/positive selection.
- **D > 0**: pi > theta_W -> excess of intermediate-frequency variants. Suggests balancing selection, population contraction, or population structure.

---

## 7. Common Mistakes

### Mistake 1: Forgetting to divide by L
- **Error**: Reporting total pairwise differences without normalizing by sequence length.
- **Fix**: Always divide by L to get a per-site measure.

### Mistake 2: Double-counting pairs
- **Error**: Counting both (i, j) and (j, i) as separate pairs, then using C(n,2) as divisor.
- **Fix**: Either iterate with i < j (upper triangle only), or iterate all pairs and divide by n(n-1) instead of C(n,2).

### Mistake 3: Confusing pi with heterozygosity
- **Clarification**: For single-site data, pi at one site equals the site heterozygosity. But pi is averaged over all L sites. They are related but not identical concepts.

### Mistake 4: Ignoring gaps and missing data
- **Fix**: Either exclude gapped sites from L and from the difference count, or handle them explicitly (pairwise deletion vs. complete deletion).

### Mistake 5: Assuming pi alone tells you about selection
- **Clarification**: Low pi can result from bottlenecks, low mutation rate, or selection. pi alone cannot distinguish these. Combine with other statistics (Tajima's D, FST, divergence) for inference.

### Mistake 6: Mixing up n and 2n
- **Fix**: n in the formula is the number of sequences (haplotypes — one sequence per chromosome copy), not the number of individuals. For 10 diploid individuals who each contribute two chromosome copies, n = 20 haplotype sequences.

---

## 8. Teaching Checkpoints

### Checkpoint 1: Explain-Back (Understanding Layer)

> **Question**: You have two populations: Population A has pi = 0.002 and Population B has pi = 0.015. Without knowing anything else, what can you say about these two populations? What additional information would you want before drawing conclusions about why they differ?

**Expected response elements**:
- Population B has ~7.5x more nucleotide diversity than Population A.
- Possible explanations: different Ne, different mutation rates, different selection pressures, different demographic histories.
- Additional information needed: Tajima's D, divergence from outgroup, knowledge of the genomic region, sample sizes.

### Checkpoint 2: Predict-Before-Run (Instruction Layer)

> **Question**: Consider these 3 sequences of length 5:
> ```
> Seq1: A A A A A
> Seq2: A A A A A
> Seq3: A A G A A
> ```
> Before computing: predict whether pi will be closer to 0 or to 0.5. Then compute it and check.

**Expected answer**:
- Prediction: Close to 0, because only one sequence differs and only at one site.
- Computation: Pairs: (1,2)=0 diffs, (1,3)=1 diff, (2,3)=1 diff. Total=2. Pairs=3. L=5.
- pi = 2 / (3 * 5) = 2/15 = 0.133.

### Checkpoint 3: Debug Challenge (Implementation Literacy Layer)

> **Question**: A student writes the following pseudocode and gets pi = 0.333 for the checkpoint 2 sequences above. Find the bug.
> ```
> total_diff = 0
> for i in 0 to n-1:
>     for j in 0 to n-1:
>         if i != j:
>             for site in 0 to L-1:
>                 if seq[i][site] != seq[j][site]:
>                     total_diff += 1
> num_pairs = n * (n - 1) / 2
> pi = total_diff / (num_pairs * L)
> ```

**Expected answer**: The bug is double-counting pairs. The loop counts both (i,j) and (j,i), giving total_diff = 4 instead of 2. But num_pairs uses C(n,2) = 3. Fix: **either** change the inner loop to `for j in i+1 to n-1` (keeping num_pairs = C(n,2)), **or** keep the full loop and change num_pairs to n*(n-1). These are alternative fixes — do not apply both.
