---
name: akamchatica_biology
description: Arabidopsis kamchatica — allotetraploid biology, HMA4 gene, and homoeolog analysis context
layer: L1
version: "2.1"
tags:
  - arabidopsis
  - kamchatica
  - allotetraploid
  - homoeolog
  - hma4
  - population-genetics
  - bio334
---

# Arabidopsis kamchatica: Allotetraploid Biology, HMA4, and Homoeolog Analysis

## 1. Species Overview

**Arabidopsis kamchatica** is an allotetraploid plant species (2n = 4x = 32) in the Brassicaceae family. It is a natural hybrid species formed by the merger of two distinct diploid genomes through interspecific hybridization followed by whole-genome duplication (allopolyploidy).

A. kamchatica has a remarkably wide geographic distribution, spanning from Japan and Taiwan through the Russian Far East (Kamchatka) to Alaska and western North America.

## 2. Parental Species

### Arabidopsis halleri (2n = 2x = 16)
- **Key trait:** Hyperaccumulator of heavy metals (zinc and cadmium)
- Can tolerate and actively concentrate toxic levels of heavy metals in its leaves
- Contains multiple tandem duplications of heavy metal transport genes

### Arabidopsis lyrata (2n = 2x = 16)
- **Key trait:** Non-accumulator of heavy metals
- A widespread species across the Northern Hemisphere
- Serves as a genomic reference within the Arabidopsis genus

## 3. Homoeologs

In an allotetraploid like A. kamchatica, duplicated gene copies derived from the two different parental species are called **homoeologs**. These are distinct from:

- **Orthologs**: Genes in different species related by speciation
- **Paralogs**: Genes within a species related by duplication within the same genome
- **Homoeologs**: Genes within a polyploid related by the hybridization event

For any given gene:
- The **halleri-derived copy** (H-homoeolog) descends from the A. halleri parent
- The **lyrata-derived copy** (L-homoeolog) descends from the A. lyrata parent

## 4. HMA4 Gene

**HMA4** (Heavy Metal ATPase 4) encodes a P-type ATPase transporter that moves zinc and cadmium from root cells into the plant's vascular system for long-distance transport to leaves. (In plant anatomy terms, it pumps metals from the symplast into the xylem.)

Key facts:
- In A. halleri: present in **multiple tandem copies** (3-4 copies), major genetic basis for hyperaccumulation
- In A. lyrata: exists as a **single copy**, does not confer hyperaccumulation
- In A. kamchatica: both halleri-derived and lyrata-derived copies are present
- The halleri-derived HMA4 homoeolog shows signs of **positive selection or selective sweep**

## 5. Research Context

Dataset from: **Paape T, Hatakeyama M, et al.** (2016) *Molecular Biology and Evolution* 33(11): 2781-2800.

### Sampling
- **20 accessions** from Japan, Alaska, and Taiwan
- Both halleri-derived and lyrata-derived HMA4 homoeologs sequenced per accession

### Analytical Goal
Do the two subgenomes show different levels of nucleotide diversity at HMA4, and if so, what does this tell us about selection?

## 6. Why This Matters for Teaching

This dataset integrates every skill learned in the course:
- Python fundamentals (FASTA parsing, string manipulation, loops)
- Algorithm design (pairwise comparison, set operations for SNP detection)
- Population genetics (pi, S, theta_w, Tajima's D)
- Biological interpretation (explaining WHY numbers differ between subgenomes)

## 7. Key Results to Expect

### Halleri-derived HMA4 (H-homoeolog)
- **pi = 0.000830** (very low nucleotide diversity)
- Consistent with a **selective sweep**

### Lyrata-derived HMA4 (L-homoeolog)
- **pi = 0.009133** (approximately 11x higher diversity)
- More typical of a neutrally evolving locus

### Net Divergence Between Subgenomes (D_a)

**D_a** (net nucleotide divergence) measures divergence between two groups corrected for within-group diversity.

**Formula:**
```
D_a = d_xy - (pi_1 + pi_2) / 2
```

where:
- **d_xy** (pi_between) = average number of pairwise differences between sequences from group 1 and group 2, divided by sequence length L
- **pi_1** = nucleotide diversity within group 1 (halleri homoeologs)
- **pi_2** = nucleotide diversity within group 2 (lyrata homoeologs)

**Computing d_xy:**
```
d_xy = (1 / (n1 * n2 * L)) * Sum over all (i in group1, j in group2) of d_ij
```

where n1 and n2 are the number of sequences in each group.

**Why correct for within-group diversity?** Raw between-group differences (d_xy) include both true divergence AND ancestral polymorphism. Subtracting the average within-group diversity removes the contribution of shared ancestral variation.

**Worked example** (using course dataset values):
```
pi_halleri = 0.000830
pi_lyrata  = 0.009133
d_xy       = 0.044122  (computed from all 20x20 between-group pairs)

D_a = 0.044122 - (0.000830 + 0.009133) / 2
    = 0.044122 - 0.004982
    = 0.039140
```

- **D_a = 0.039140** for the HMA4 region

### Biological Interpretation
The ~11-fold difference in pi strongly suggests the halleri-derived HMA4 has experienced **directional selection** in A. kamchatica. Since HMA4 is the key gene for heavy metal hyperaccumulation -- a trait inherited from A. halleri -- the functionally important copy has been maintained by selection, sweeping away neutral variation.

## 8. Teaching Checkpoints

**Checkpoint 1:** The halleri-derived HMA4 shows pi = 0.000830 while the lyrata-derived copy shows pi = 0.009133. Propose a biological explanation for this ~11-fold difference.

*Expected reasoning:* Positive selection (selective sweep) on the halleri-derived copy reduces linked neutral variation. The lyrata-derived copy, less functionally constrained for metal transport, retains higher neutral diversity.

**Checkpoint 2:** Why is it important that samples were collected from geographically diverse locations (Japan, Alaska, Taiwan) rather than from a single population?

*Expected reasoning:* Broader sampling captures species-wide variation, but population structure (Wahlund effect) could affect diversity statistics. Trade-off between sampling breadth and assumptions of standard population genetic models.
