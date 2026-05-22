---
name: popgen_tajimas_d
description: Tajima's D — theory, calculation procedure, biological interpretation, and connection to the Wright-Fisher model
layer: L1
version: "1.4"
tags:
  - population-genetics
  - tajimas-d
  - neutrality-test
  - teaching
  - bio334
---

# Tajima's D

> **Prerequisites**: Before working through this file, ensure you understand nucleotide diversity (pi) from `popgen_nucleotide_diversity` and segregating sites (S, theta_w) from `popgen_segregating_sites`.

## 1. What is Tajima's D?

Tajima's D is a population genetics statistic that tests the **neutral theory of molecular evolution**. It was proposed by Fumio Tajima in 1989.

The core idea is elegant: under neutral evolution in a constant-size population, **two different estimators of the population mutation parameter theta (= 4N*mu) should give the same value**. Tajima's D measures the discrepancy between them:

| Estimator | Based on | Symbol |
|-----------|----------|--------|
| Pairwise nucleotide diversity | Average number of pairwise differences | pi |
| Watterson's estimator | Number of segregating sites | theta_w |

- If pi approx theta_w -> consistent with neutral evolution (D approx 0)
- If pi != theta_w -> something interesting is happening (selection, demography, etc.)

**Key insight**: pi is sensitive to the *frequency* of variants, while theta_w only counts whether a site is polymorphic or not. This difference in sensitivity is what gives Tajima's D its power.

---

## 2. Mathematical Definition

### 2.1 The Two Estimators

Given **n** aligned sequences of length **L**:

**Watterson's estimator (theta_w):**

```
theta_w = S / a_1
```

where:
- **S** = number of segregating (polymorphic) sites -- this is a count, not a rate
- a_1 = Sum(1/i) for i = 1 to n-1 (the (n-1)th harmonic number)

**Pairwise nucleotide diversity (pi):**

```
pi = Sum_{i<j} d_ij / C(n,2)
```

where:
- d_ij = number of nucleotide differences between sequences i and j
- C(n,2) = n(n-1)/2 = number of pairwise comparisons

**Note on units**: In this formula, both pi and theta_w are expressed as **total counts** (per-sequence), not per-site values. This is different from `popgen_nucleotide_diversity`, which defines pi as per-site (dividing by sequence length L). For Tajima's D, either convention works as long as both estimators use the same units — L cancels in the ratio d / sqrt(V(d)).

**If you computed pi per-site** (as in `popgen_nucleotide_diversity`), multiply by L to convert to total counts before using Tajima's D, or equivalently compute theta_w per-site as S / (a_1 * L). The D value is identical either way.

### 2.2 Tajima's D Statistic

```
D = d / sqrt(V(d))
```

where:
- d = pi - theta_w

### 2.3 Variance Estimation (Tajima 1989)

> **For students**: You do not need to memorize or derive the formulas below. They are standard coefficients from coalescent theory that ensure Tajima's D is properly scaled. The key idea is that V(d) depends only on **n** (number of sequences) and **S** (number of segregating sites) — no new data is needed. AI will compute these for you. Your job is to verify that the final D value makes biological sense (see Section 3).

The variance of d is estimated as:

```
V(d) = e_1 * S + e_2 * S * (S - 1)
```

where the coefficients are derived from coalescent theory:

```
e_1 = c_1 / a_1
e_2 = c_2 / (a_1^2 + a_2)
```

with:

```
a_1 = Sum(1/i)      for i = 1 to n-1
a_2 = Sum(1/i^2)    for i = 1 to n-1

b_1 = (n + 1) / (3 * (n - 1))
b_2 = 2 * (n^2 + n + 3) / (9 * n * (n - 1))

c_1 = b_1 - 1/a_1
c_2 = b_2 - (n + 2)/(a_1 * n) + a_2/a_1^2
```

**Why so many intermediate variables?** Each coefficient corrects for the fact that pi and theta_w have different sampling properties. The normalization ensures that D values between roughly -2 and +2 are "expected" under neutrality, regardless of sample size.

**Note:** Under the null hypothesis (neutral evolution, constant population size), D approximately follows a beta distribution, not a normal distribution.

---

## 3. Biological Interpretation

### D approx 0: Neutral Baseline
- Consistent with neutral evolution in a constant-size population
- The two estimators agree: the site frequency spectrum matches neutral expectations

### D > 0: Excess of Intermediate-Frequency Variants

| Cause | Mechanism |
|-------|-----------|
| Balancing selection | Selection maintains multiple alleles at intermediate frequencies |
| Population bottleneck | Rare variants lost preferentially; remaining variants drift to intermediate frequencies |
| Population structure | Sampling from subdivided populations inflates intermediate-frequency variants |

### D < 0: Excess of Rare Variants (Singletons)

| Cause | Mechanism |
|-------|-----------|
| Population expansion | New mutations accumulate on the expanding genealogy but remain at low frequency |
| Positive (directional) selection | A selective sweep reduces diversity; new mutations post-sweep are all rare |
| Purifying (negative) selection | Deleterious alleles kept at low frequency by selection against them |

**Important caveat**: Tajima's D alone cannot distinguish between selection and demography. Demographic effects are genome-wide, while selection acts on specific loci.

---

## 4. Step-by-Step Algorithm

Given a multiple sequence alignment of n sequences, each of length L:

```
STEP 1: Count segregating sites (S)
STEP 2: Compute pairwise nucleotide diversity (pi)
   pi = sum of all d_ij / C(n, 2)
STEP 3: Compute Watterson's estimator (theta_w)
   a_1 = 1/1 + 1/2 + ... + 1/(n-1)
   theta_w = S / a_1
STEP 4: Compute the difference
   d = pi - theta_w
STEP 5: Compute the variance V(d)
   a_2 = 1/1^2 + 1/2^2 + ... + 1/(n-1)^2
   b_1 = (n + 1) / (3*(n - 1))
   b_2 = 2*(n^2 + n + 3) / (9*n*(n - 1))
   c_1 = b_1 - 1/a_1
   c_2 = b_2 - (n + 2)/(a_1 * n) + a_2/a_1^2
   e_1 = c_1 / a_1
   e_2 = c_2 / (a_1^2 + a_2)
   V(d) = e_1 * S + e_2 * S * (S - 1)
STEP 6: Compute Tajima's D
   D = d / sqrt(V(d))
```

---

## 5. Worked Example

### Input: 4 sequences, 10 sites each

```
Seq1: A T G C A T G C A T
Seq2: A T G C A T G T A T
Seq3: A C G C G T G C A T
Seq4: A C G C G T A C A A
```

**n = 4, L = 10**

### Step 1: S = 5 segregating sites (positions 2, 5, 7, 8, 10)

### Step 2: Pairwise differences
- (1,2)=1, (1,3)=2, (1,4)=4, (2,3)=3, (2,4)=5, (3,4)=2
- Sum = 17, C(4,2) = 6
- pi = 17 / 6 = 2.8333 (total-count convention; per-site would be 2.8333 / 10 = 0.2833)

### Step 3: theta_w
- a_1 = 1 + 0.5 + 0.333 = 1.8333
- theta_w = 5 / 1.8333 = 2.7273

### Step 4: d = 2.8333 - 2.7273 = 0.1061

### Step 5: Variance
- a_2 = 1 + 0.25 + 0.111 = 1.3611
- b_1 = 5/9 = 0.5556, b_2 = 46/108 = 0.4259
- c_1 = 0.0101, c_2 = 0.0127
- e_1 = 0.0055, e_2 = 0.00269
- V(d) = 0.0055*5 + 0.00269*5*4 = 0.0813

### Step 6: D = 0.1061 / sqrt(0.0813) = 0.1061 / 0.2851 = 0.372

**Interpretation**: D = 0.37, a small positive value close to zero. Consistent with neutral evolution.

---

## 6. Connection to the Wright-Fisher Model

### No Mutation (mu = 0)
- Diversity -> 0, D tends negative before becoming undefined

### With Mutation, Constant Population
- pi fluctuates around theta = 4N*mu
- D fluctuates around 0

### Population Expansion
- Star-shaped genealogy, many singletons
- pi < theta_w -> D < 0

### Population Bottleneck
- Rare variants lost, intermediate-frequency variants remain
- pi > theta_w -> D > 0

---

## 7. Common Mistakes

- **Confusing per-site normalization with the Watterson correction**: theta_w = S/a_1, not S/L. Dividing S by L gives a per-site proportion of segregating sites, which is a different quantity.
- **Mixing per-site and per-sequence units**: Both pi and theta_w must use the same convention. If pi is per-site (divided by L), theta_w must also be per-site (S / (a_1 * L)).
- **Forgetting the harmonic number**: theta_w = S / a_1, NOT simply S.
- **Assuming D follows a normal distribution**: The null distribution is approximately beta.
- **Interpreting D in isolation**: Combine with other tests and biological context.
- **Small sample size over-interpretation**: With n < 10, D has large variance.

---

## 8. Teaching Checkpoints

### Checkpoint 1: Explain-Back
> Explain why population expansion leads to a negative Tajima's D. Reference the shape of the genealogical tree and how it affects the site frequency spectrum.

### Checkpoint 2: Predict-Before-Run
> You have 20 sequences from a population that recently experienced a severe bottleneck followed by recovery. Predict: Will Tajima's D be positive, negative, or near zero?

### Checkpoint 3: Debug Challenge
> A student computes theta_w = S/L = 25/1000 = 0.025 instead of S/a_1. Find and explain the error.

---

## References

- Tajima, F. (1989). "Statistical method for testing the neutral mutation hypothesis by DNA polymorphism." *Genetics*, 123(3), 585-595.
