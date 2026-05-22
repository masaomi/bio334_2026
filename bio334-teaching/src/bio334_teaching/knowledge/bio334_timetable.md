---
name: bio334_timetable
description: BIO334 minute-level timetable — lecture, hands-on, checkpoint, discussion, and break schedules for a 3-day intensive module
layer: L1
version: "1.1"
tags:
  - timetable
  - schedule
  - bio334
  - teaching
  - time-management
---

# BIO334 Timetable -- Minute-Level Schedule

## Overview

- **Duration**: 3 days (14-16 May 2025)
- **Daily schedule**: 09:00-16:00 (7 hours, 1 hour lunch)
- **Effective teaching time**: ~300 minutes/day
- **Total**: ~900 minutes across 3 days

## Activity Types

| Type | Icon | Description | Typical Duration |
|------|------|-------------|-----------------|
| lecture | Lecture | Concept explanation (Teaching Chain leads) | 15-25 min |
| hands_on | Hands-on | Coding exercise (student + AI collaboration) | 25-40 min |
| checkpoint | Checkpoint | Understanding check (Explain-Back, Predict-Before-Run, Debug Challenge, AI Code Verification) | 5-10 min |
| discussion | Discussion | Q&A, class discussion | 5-15 min |
| break | Break | Rest break | 10-15 min |
| review | Review | Recap of previous session | 5-10 min |
| demo | Demo | Live demo / walkthrough | 10-15 min |

## Day 1: Foundations (09:00-16:00)

### Morning Session (09:00-12:00)

| Time | Duration | Type | Topic | Skill Reference | Notes |
|------|----------|------|-------|-----------------|-------|
| 09:00-09:20 | 20 min | lecture | Course introduction & AI tools overview | agentic_coding_pedagogy | Explain agentic coding philosophy; introduce tools (Claude, Cursor, etc.) |
| 09:20-09:30 | 10 min | checkpoint | Python experience assessment | python_basics_for_bio | Quick self-assessment: variables, loops, functions familiarity |
| 09:30-10:00 | 30 min | hands_on | Python quick review | python_basics_for_bio | Scaffold: guided. Variables, types, control flow, data structures |
| 10:00-10:15 | 15 min | break | -- | -- | -- |
| 10:15-10:35 | 20 min | lecture | Two sequences comparison | popgen_nucleotide_diversity | Pairwise comparison concept; counting nucleotide differences |
| 10:35-10:45 | 10 min | demo | Live coding: comparing two sequences | python_basics_for_bio | Show the for-loop pattern for character-by-character comparison |
| 10:45-11:25 | 40 min | hands_on | Exercise: pairwise sequence comparison | popgen_nucleotide_diversity | Scaffold: guided to partial. Students implement difference counting |
| 11:25-11:35 | 10 min | checkpoint | Explain-Back: what does the difference count mean? | popgen_nucleotide_diversity | "Explain to a non-biologist what we just computed" |
| 11:35-11:45 | 10 min | discussion | Questions & clarification | -- | Open Q&A |
| 11:45-12:00 | 15 min | lecture | Nucleotide diversity (pi) introduction | popgen_nucleotide_diversity | Definition, formula, biological meaning |

### Lunch Break (12:00-13:00)

### Afternoon Session (13:00-16:00)

| Time | Duration | Type | Topic | Skill Reference | Notes |
|------|----------|------|-------|-----------------|-------|
| 13:00-13:10 | 10 min | review | Recap: pairwise differences to pi | popgen_nucleotide_diversity | Quick review of morning concepts |
| 13:10-13:30 | 20 min | lecture | pi: from pairs to populations | popgen_nucleotide_diversity | All-pairs comparison, normalization by C(n,2) x L |
| 13:30-13:40 | 10 min | checkpoint | Predict-Before-Run: estimate pi for small dataset | popgen_nucleotide_diversity | Students predict before computing |
| 13:40-14:20 | 40 min | hands_on | Exercise: nucleotide diversity calculation | popgen_nucleotide_diversity | Scaffold: partial. Skeleton code provided |
| 14:20-14:35 | 15 min | break | -- | -- | -- |
| 14:35-14:55 | 20 min | lecture | File I/O and FASTA format | python_file_io_parsing, bioinformatics_file_formats | Data/code separation, FASTA structure, multi-line sequences |
| 14:55-15:05 | 10 min | demo | FASTA parsing walkthrough | python_file_io_parsing | Show the parsing algorithm; explain sys.argv |
| 15:05-15:40 | 35 min | hands_on | Exercise: pi from FASTA file | python_file_io_parsing | Scaffold: partial. Combine FASTA reading + pi calculation |
| 15:40-15:50 | 10 min | checkpoint | Debug Challenge: find the parsing bug | python_file_io_parsing | Multi-line FASTA handling error |
| 15:50-16:00 | 10 min | discussion | Day 1 wrap-up & preview | bio334_curriculum_map | Summary; what comes tomorrow |

**Day 1 Totals**: Lecture 80 min | Hands-on 145 min | Checkpoint 40 min | Discussion 20 min | Break 30 min | Review 10 min | Demo 20 min

---

## Day 2: Core Algorithms & Real Data (09:00-16:00)

### Morning Session (09:00-12:00)

| Time | Duration | Type | Topic | Skill Reference | Notes |
|------|----------|------|-------|-----------------|-------|
| 09:00-09:10 | 10 min | review | Recap Day 1: pi calculation from files | popgen_nucleotide_diversity | Brief review |
| 09:10-09:30 | 20 min | lecture | Functions and reusability | python_functions_modules | def, parameters, return; refactoring inline to function |
| 09:30-09:40 | 10 min | demo | Refactoring: script to function to module | python_functions_modules | Live refactoring of yesterday's code |
| 09:40-10:10 | 30 min | hands_on | Exercise: create nucleotide_diversity() function | python_functions_modules | Scaffold: partial to autonomous |
| 10:10-10:20 | 10 min | checkpoint | "What function signature would you give AI?" | python_functions_modules | Instruction literacy check |
| 10:20-10:35 | 15 min | break | -- | -- | -- |
| 10:35-10:55 | 20 min | lecture | Segregating sites & Watterson's theta_w | popgen_segregating_sites | Definition, Set-based algorithm, harmonic number |
| 10:55-11:30 | 35 min | hands_on | Exercise: detect segregating sites | popgen_segregating_sites | Using Python Set for SNP detection |
| 11:30-11:40 | 10 min | checkpoint | Explain-Back: theta_w vs pi, why two estimators? | popgen_segregating_sites | Conceptual understanding of the two estimators |
| 11:40-12:00 | 20 min | lecture | Tajima's D: theory & biological meaning | popgen_tajimas_d | Formula, interpretation (D>0, D<0, D approx 0) |

### Lunch Break (12:00-13:00)

### Afternoon Session (13:00-16:00)

| Time | Duration | Type | Topic | Skill Reference | Notes |
|------|----------|------|-------|-----------------|-------|
| 13:00-13:15 | 15 min | lecture | Tajima's D: variance estimation & worked example | popgen_tajimas_d | Walk through the full calculation |
| 13:15-13:55 | 40 min | hands_on | Exercise: Tajima's D implementation | popgen_tajimas_d | Core exercise. Scaffold: partial |
| 13:55-14:05 | 10 min | checkpoint | Predict-Before-Run: simulation predictions | popgen_wright_fisher | "What happens to D with population expansion?" |
| 14:05-14:20 | 15 min | break | -- | -- | -- |
| 14:20-14:40 | 20 min | lecture | Wright-Fisher model & simulation | popgen_wright_fisher | Marble jar analogy, parameters, what simulations show |
| 14:40-14:50 | 10 min | demo | Running WF simulation, interpreting output | popgen_wright_fisher | Show pi and D trajectories under different scenarios |
| 14:50-15:00 | 10 min | discussion | Biological interpretation of simulation results | popgen_wright_fisher | Why D goes negative with expansion, positive with bottleneck |
| 15:00-15:15 | 15 min | lecture | Batch processing & A. kamchatica introduction | python_batch_processing, akamchatica_biology | Shell scripts, glob/os; allotetraploid, homoeolog, HMA4 |
| 15:15-15:50 | 35 min | hands_on | Exercise: A. kamchatica homoeolog analysis | akamchatica_biology, python_batch_processing | Culminating exercise: batch pi for halleri vs lyrata |
| 15:50-16:00 | 10 min | discussion | Day 2 wrap-up: interpreting subgenome differences | akamchatica_biology | Why is pi_halleri so low? Selective sweep hypothesis |

**Day 2 Totals**: Lecture 90 min | Hands-on 140 min | Checkpoint 30 min | Discussion 20 min | Break 30 min | Review 10 min | Demo 20 min

---

## Day 3: Advanced Analysis & Integration (09:00-16:00)

### Morning Session (09:00-12:00)

| Time | Duration | Type | Topic | Skill Reference | Notes |
|------|----------|------|-------|-----------------|-------|
| 09:00-09:15 | 15 min | review | Recap Day 2: Tajima's D + A. kamchatica results | popgen_tajimas_d, akamchatica_biology | Review key results |
| 09:15-09:35 | 20 min | lecture | VCF format & advanced file processing | bioinformatics_file_formats, python_file_io_parsing | VCF columns, genotype encoding, 1-based coords |
| 09:35-09:45 | 10 min | demo | VCF parsing walkthrough | bioinformatics_file_formats | Show dictionary-based SNP storage |
| 09:45-10:15 | 30 min | hands_on | Exercise: parse VCF and extract genotypes | bioinformatics_file_formats | Scaffold: partial |
| 10:15-10:30 | 15 min | break | -- | -- | -- |
| 10:30-10:50 | 20 min | lecture | pi from VCF: new pipeline | popgen_nucleotide_diversity | Computing diversity from variant-only data |
| 10:50-11:40 | 50 min | hands_on | Exercise: nucleotide diversity from VCF | popgen_nucleotide_diversity, bioinformatics_file_formats | Advanced exercise with A. thaliana 1001 Genomes data |
| 11:40-11:50 | 10 min | checkpoint | Debug Challenge: coordinate system mismatch | bioinformatics_file_formats | VCF 1-based vs Python 0-based |
| 11:50-12:00 | 10 min | discussion | Comparing FASTA-based vs VCF-based analysis | -- | Pros and cons of each approach |

### Lunch Break (12:00-13:00)

### Afternoon Session (13:00-16:00)

| Time | Duration | Type | Topic | Skill Reference | Notes |
|------|----------|------|-------|-----------------|-------|
| 13:00-13:15 | 15 min | lecture | Net divergence D_a & subgenome comparison | akamchatica_biology | D_a formula, biological meaning |
| 13:15-14:00 | 45 min | hands_on | Exercise: complete A. kamchatica analysis pipeline | akamchatica_biology, python_batch_processing | Scaffold: autonomous. pi + D_a for both subgenomes |
| 14:00-14:15 | 15 min | break | -- | -- | -- |
| 14:15-14:35 | 20 min | checkpoint | Final comprehensive check | All skills | Explain-Back: "Why is pi_halleri << pi_lyrata?" + AI Code Verification of student pipeline |
| 14:35-15:00 | 25 min | discussion | Biological interpretation & course synthesis | agentic_coding_pedagogy | What did we learn? Agentic coding reflection |
| 15:00-15:30 | 30 min | lecture | Looking ahead: real-world pipelines & tools | agentic_coding_pedagogy | Snakemake, nextflow, BioPython; how agentic skills transfer |
| 15:30-15:50 | 20 min | discussion | Open Q&A and feedback | -- | Course evaluation, future directions |
| 15:50-16:00 | 10 min | lecture | Closing remarks | -- | Final exam preview, resources |

**Day 3 Totals**: Lecture 85 min | Hands-on 125 min | Checkpoint 30 min | Discussion 55 min | Break 30 min | Review 15 min | Demo 10 min

---

## Summary: Time Allocation Across 3 Days

| Activity | Day 1 | Day 2 | Day 3 | Total | % |
|----------|-------|-------|-------|-------|---|
| Lecture | 80 min | 90 min | 85 min | **255 min** | 28% |
| Hands-on | 145 min | 140 min | 125 min | **410 min** | 46% |
| Checkpoint | 40 min | 30 min | 30 min | **100 min** | 11% |
| Discussion | 20 min | 20 min | 55 min | **95 min** | 11% |
| Break | 30 min | 30 min | 30 min | **90 min** | -- |
| Review | 10 min | 10 min | 15 min | **35 min** | 4% |
| Demo | 20 min | 20 min | 10 min | **50 min** | -- |

**Key ratio**: Hands-on (46%) > Lecture (28%) > Checkpoint + Discussion (22%) > Review + Demo (4%)

## Scheduling Guidelines for the Teaching Chain

### Time Awareness
- The Teaching Chain should track which time block the student is currently in
- Adjust behavior based on activity type:
  - During lecture: explain concepts, minimize code
  - During hands_on: answer questions, provide hints progressively
  - During checkpoint: ask questions, evaluate responses
  - During discussion: facilitate, summarize

### Flexibility Rules
- If a student is struggling: extend hands_on by borrowing from discussion time
- If a student finishes early: offer extension problems or move to next topic
- If a checkpoint reveals misunderstanding: insert a mini-review before proceeding
- Never skip break -- cognitive fatigue degrades learning

### Pacing Indicators
- On track: student completes exercises within allocated time
- Falling behind: student needs >50% more time than allocated
- Ahead: student finishes >30% before time is up -> offer advanced variant

### Session Handoff
- At end of each day: save progress to student progress data
- At start of next day: read student progress to determine resume point
- If student missed a day: provide compressed review of key concepts
