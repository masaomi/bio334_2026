# BIO334 Curriculum Map (Summary)

## Course: BIO334 Practical Bioinformatics -- Module 2
- 3-day intensive (14-16 May 2025)
- Theme: Population genetics with Python
- Final goal: A. kamchatica homoeolog nucleotide diversity analysis

## Day 1: Fundamentals
- Python quick review (variables, types, control flow)
- Pairwise sequence comparison
- Nucleotide diversity (pi) introduction + File I/O (FASTA)

## Day 2: Core Algorithms & Real Data
- Functions & modules (refactoring)
- Segregating sites & Watterson's theta_w
- Tajima's D calculation (core topic)
- Wright-Fisher simulation
- Batch processing & A. kamchatica homoeolog analysis

## Day 3: Advanced (VCF Processing)
- VCF format parsing
- pi from VCF (A. thaliana 1001 Genomes)
- Complete A. kamchatica pipeline (pi + D_a)

## Final Exam Expected Values
- halleri pi = 0.000830, lyrata pi = 0.009133, D_a = 0.039140

## Skill Dependency Graph
- python_basics -> file_io -> functions -> batch_processing
- nucleotide_diversity -> segregating_sites -> tajimas_d -> wright_fisher
- bioinformatics_file_formats (cross-cutting)
