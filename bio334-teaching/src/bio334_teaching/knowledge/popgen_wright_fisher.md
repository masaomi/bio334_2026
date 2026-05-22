---
name: popgen_wright_fisher
description: Wright-Fisher model — population genetics simulation, genetic drift, and numerical verification of neutral theory
layer: L1
version: "1.2"
tags:
  - population-genetics
  - wright-fisher
  - simulation
  - genetic-drift
  - neutral-theory
  - teaching
  - bio334
---

# Wright-Fisher Model -- Population Genetics Simulation

## 1. What is the Wright-Fisher Model?

The Wright-Fisher model is the most fundamental population genetics simulation. It models the transmission of alleles from one generation to the next as a process of **random sampling**. Despite its simplicity, it captures the essential dynamics of genetic drift -- the stochastic changes in allele frequencies that occur in finite populations.

The model provides a computational bridge between theoretical predictions (e.g., expected heterozygosity, fixation time) and observable patterns in real sequence data.

## 2. Assumptions

- **Haploid population**: Each individual carries a single copy of the genome.
- **Constant population size**: The population has exactly N individuals in every generation.
- **No natural selection**: All individuals have equal fitness. Purely random sampling (neutral evolution).
- **Point nucleotide mutation only**: Mutations are single-nucleotide substitutions at rate mu per site per generation. No recombination, no structural variants.

## 3. The Marble Jar Analogy

Imagine a jar containing N marbles, each representing an individual's DNA sequence.

To create the next generation:
1. Draw one marble at random from the jar.
2. Copy it (possibly introducing a small mutation).
3. Place the copy in a new jar.
4. Repeat N times (sampling with replacement).
5. Discard the old jar.

Because sampling is random with replacement, some sequences will be copied multiple times, while others will leave no descendants. Over many generations, this process causes lineages to be lost -- this is **genetic drift**.

## 4. Simulation Algorithm

### Initialize
- Create N identical DNA sequences, each of length L nucleotides.

### Each Generation (repeat for T generations)
1. **Random sampling**: Draw N sequences from the current population with replacement.
2. **Apply point mutations**: For each nucleotide in each sequence, with probability mu, replace it with a randomly chosen different nucleotide.
3. **Replace**: The sampled-and-mutated sequences become the new population.

### Track Statistics Over Generations
- **Segregating sites (S)**
- **Nucleotide diversity (pi)**
- **Tajima's D**

## 5. Key Parameters

| Parameter | Symbol | Meaning |
|-----------|--------|---------|
| Population size | N | Number of haploid individuals |
| Sequence length | L | Number of nucleotide sites per sequence |
| Mutation rate | mu | Probability of mutation per site per generation |
| Generations | T | Number of generations to simulate |
| Expected diversity | theta = 2N*mu | For haploid populations, the expected nucleotide diversity at equilibrium |

## 6. What the Simulations Show

### Scenario A: No mutation (mu = 0)
- Diversity -> 0: drift eliminates variation.
- Tajima's D becomes undefined when S reaches 0 (because V(d) = 0 and division by zero occurs). Before that point, the trajectory of D is stochastic and depends on which variants are lost last.

### Scenario B: With mutation (mu > 0, constant N)
- Diversity stabilizes at mutation-drift equilibrium.
- pi approx theta = 2N*mu (per site) at equilibrium.
- Tajima's D fluctuates around 0.

### Scenario C: Population expansion (N increases suddenly)
- Excess of rare variants.
- Tajima's D < 0.

### Scenario D: Population bottleneck (N decreases temporarily)
- Loss of rare variants.
- Tajima's D > 0.

### Scenario E: Positive selection (selective sweep)
- **Note**: This scenario is NOT part of the basic Wright-Fisher model described above (which assumes no selection). It is included for biological comparison, because the pattern it produces — reduced diversity and negative Tajima's D — resembles what we observe in the halleri-derived HMA4 homoeolog.
- Diversity reduction around the selected site.
- Tajima's D < 0.

## 7. Why Simulation Matters for Learning

1. **Validates theoretical predictions numerically**: Students can verify that pi converges to 2N*mu.
2. **Builds intuition about stochastic processes**: Simulation reveals variance, not just expected values.
3. **Connects theory to data analysis**: The same statistics computed in simulation are computed on real genomic data.

## 8. Teaching Checkpoints

### Checkpoint 1: Population Size and Variance
> "If we double N, what happens to the variance of pi?"

Expected: Variance decreases (less drift per generation). Mean pi increases (theta = 2N*mu).

### Checkpoint 2: Mutation Rate Zero
> "If mutation rate = 0, will all sequences eventually become identical?"

Expected: Yes. Without mutation, drift eventually fixes one sequence. Fixation time is proportional to N.

### Checkpoint 3: Population Expansion and Tajima's D
> "After a sudden population expansion, is Tajima's D positive or negative?"

Expected: Negative. Many new rare mutations inflate S and theta_w, but pi remains low because these variants are at low frequency.
