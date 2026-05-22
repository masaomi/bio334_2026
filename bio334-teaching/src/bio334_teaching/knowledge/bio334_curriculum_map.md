---
name: bio334_curriculum_map
description: BIO334 Practical Bioinformatics curriculum structure map — progressive learning design from Day 1 to Day 3 + Final Exam with skill dependency graph
layer: L1
version: "2.0"
tags:
  - curriculum
  - bio334
  - teaching
  - structure
  - progression
  - population-genetics
---

# BIO334 Curriculum Map

## Course Overview

- **Course Name**: BIO334 Practical Bioinformatics -- Module 2
- **Instructor**: Dr. Masaomi Hatakeyama (UZH / FGCZ)
- **Duration**: 3-day intensive (14-16 May, 2025)
- **Theme**: Solving population genetics problems with Python
- **Final Goal**: Homoeolog nucleotide diversity analysis of A. kamchatica

## Four-Layer Competency Model

Each topic targets one or more layers:
- **L1 (Conceptual Understanding)**: Can the student explain what is being computed?
- **L2 (Instruction)**: Can the student give precise instructions to AI?
- **L3 (Implementation Literacy)**: Can the student read and verify the code?
- **L4 (Verification)**: Can the student interpret results biologically?

## Progressive Structure of Learning Objectives

```
[Python basics] -> [File operations] -> [Functions] -> [Summary statistics] -> [Simulation] -> [Real data analysis]
     |              |              |              |                |                 |
   Variables     FASTA parsing   Reusability    pi, theta_w, D  Wright-Fisher    A. kamchatica
   & types       sys.argv       def/return    segregating     genetic drift     HMA4 gene
   Control flow  open/read      module        sites           mutation model    halleri vs lyrata
```

## Day 1: Fundamentals -> Pairwise Comparison -> Introduction to pi

### Part 1: Python Quick Review
- **Concepts**: Variables, types, operators, data structures (List, Tuple, Set, Dict), control flow
- **Agentic component**: Introduction to AI coding tools (ChatGPT, Claude, Cursor, Windsurf)
- **Learning outcome**: Recall basic Python syntax / Give basic instructions to AI assistants
- **Primary layers**: L1 (Conceptual), L2 (Instruction)
- **Dependencies**: None (prerequisite knowledge)

### Part 2: Two Sequences Comparison
- **Concepts**: Counting nucleotide differences between two sequences
- **Core algorithm**: Character-by-character comparison using a for loop, counting differences
- **Learning outcome**: Understand the basic pattern of pairwise comparison
- **Primary layers**: L1 (Conceptual), L3 (Implementation)
- **Dependencies**: Part 1 (variables, loops, conditionals)

### Part 3: Nucleotide Diversity (Introduction)
- **Concepts**: Definition and meaning of pi (nucleotide diversity)
- **Formula**: pi = (2 / n(n-1)) * Sum(d_ij / L)
- **Learning outcome**: Explain the meaning of pi and perform manual calculations on small datasets
- **Primary layers**: L1 (Conceptual), L3 (Implementation)
- **Dependencies**: Part 2 (pairwise comparison)

## Day 2: File Operations -> Summary Statistics -> Real Data

### Part 1: Nucleotide Diversity Part 2 -- File I/O
- **Concepts**: FASTA format, file reading, command-line arguments (sys.argv)
- **Core idea**: Separation of data and process (reusability)
- **Learning outcome**: Write a script that calculates pi from a FASTA file
- **Primary layers**: L2 (Instruction), L3 (Implementation)
- **Dependencies**: Day 1 Part 3 (pi calculation)

### Part 2: Functions & Methods
- **Concepts**: Function definition (def), arguments, return values, code generalization
- **Core idea**: Abstracting nucleotide diversity calculation as a function
- **Learning outcome**: Define and call reusable functions
- **Primary layers**: L2 (Instruction), L3 (Implementation)
- **Dependencies**: Part 1 (file operations + pi calculation)

### Part 3: Segregating Sites
- **Concepts**: SNP detection, segregating sites, Set operations
- **Core idea**: Checking allelic diversity at each position -> counting segregating sites
- **Learning outcome**: Implement an algorithm to detect segregating sites
- **Primary layers**: L1 (Conceptual), L2 (Instruction), L3 (Implementation)
- **Dependencies**: Part 2 (function abstraction)

### Part 4: Tajima's D Calculation (Core Topic)
- **Concepts**: Tajima's D = d / sqrt(V(d)), definition of d (pi - theta_w), estimation of V(d)
- **Biological interpretation**:
  - D = 0: Neutral evolution (constant population size)
  - D > 0: Excess of intermediate-frequency variants (balancing selection, bottleneck)
  - D < 0: Excess of rare variants (population expansion, directional selection)
- **Wright-Fisher Model**: Genetic drift simulation
  - Parameters: population size, sequence length, mutation rate, generations
  - Behavior of pi and Tajima's D changes with and without mutation
- **Learning outcome**: Implement Tajima's D and interpret results by comparing with simulation output
- **Primary layers**: L1 (Conceptual), L2 (Instruction), L3 (Implementation), L4 (Verification)
- **Dependencies**: Part 3 (segregating sites) + Day 1 Part 3 (pi)

### Part 5: Batch Processing & A. kamchatica (Integrative Exercise)
- **Concepts**: Batch processing (shell script, Python glob/os), module import
- **Biological subject**:
  - A. kamchatica: allotetraploid (A. halleri x A. lyrata)
  - Homoeolog analysis around the HMA4 gene (heavy metal ATPase 4)
  - 20 accessions (Japan, Alaska, Taiwan)
  - Comparison of pi between halleri-derived and lyrata-derived subgenomes
- **Learning outcome**: Implement batch analysis of multiple genes and compare diversity between subgenomes
- **Primary layers**: L2 (Instruction), L3 (Implementation), L4 (Verification)
- **Dependencies**: Part 4 (Tajima's D) + integration of all parts

## Day 3: Advanced Exercise -- VCF Processing

### VCF File Processing
- **Concepts**: VCF format, Dictionary usage, sample comparison using Set operations
- **Data**: A. thaliana 1001 Genomes Project
- **Learning outcome**: Build a new pipeline to calculate nucleotide diversity from VCF files
- **Primary layers**: L2 (Instruction), L3 (Implementation), L4 (Verification)
- **Dependencies**: All of Day 2

## Final Exam: A. kamchatica HMA4 Analysis

### Question 1: Reference Sequence Loading (5 points)
- FASTA file reading, sequence length calculation
- **Knowledge tested**: File I/O, FASTA parsing

### Question 2: Nucleotide Diversity Calculation (10 points)
- Calculate pi from VCF files
- halleri: pi = 0.000830 / lyrata: pi = 0.009133
- **Knowledge tested**: pi calculation, VCF parsing, batch processing

### Question 3: Net Divergence D_a Calculation (10 points)
- D_a = pi_between - (pi_1 + pi_2) / 2
- Expected: D_a = 0.039140
- **Knowledge tested**: Subgenome comparison, applied population genetics

## Skill Dependency Graph

```
python_basics_for_bio
    +-- python_file_io_parsing
    |   +-- python_functions_modules
    |       +-- python_batch_processing
    |
    +-- popgen_nucleotide_diversity
        +-- popgen_segregating_sites
        |   +-- popgen_tajimas_d
        |       +-- popgen_wright_fisher (deepening theoretical understanding)
        |
        +-- akamchatica_biology (biological context)
            +-- [Final Integration: A. kamchatica HMA4 Analysis]

bioinformatics_file_formats (cross-cutting knowledge)
    +-- FASTA -> used in Day 1-2
    +-- VCF -> used in Day 3 + Final Exam
```

## Guidelines for Use in Teaching Chain

### Assessment of New Learners
1. Check Python experience -> start from the appropriate phase
2. Check biological background -> adjust depth of conceptual explanations
3. Check AI tool experience -> adjust the degree of agentic scaffolding

### Route Branching Based on Progress
- **Fast track**: Has Python experience + biological understanding -> start from Day 2 Part 4
- **Standard**: Has Python basics -> start from Day 1 Part 2
- **Foundation**: Python beginner -> start carefully from Day 1 Part 1

### Continuity Between Sessions
- Progress is automatically tracked across four dimensions (L1-L4) per topic
- Check student progress at session start to resume from the appropriate point
- Automatically insert review for topics with low comprehension
