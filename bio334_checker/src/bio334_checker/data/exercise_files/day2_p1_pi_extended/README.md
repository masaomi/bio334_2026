# Day 2, Part 1 — input data

The exercise expects `athal_genome.fa` (the *A. thaliana* genome FASTA,
~120 MB uncompressed). Because of size we do NOT ship it inside the
Python package.

To activate this exercise:

```bash
gunzip -c /path/to/athal_genome.fa.gz > \
  src/bio334_checker/data/exercise_files/day2_p1_pi_extended/athal_genome.fa
```

Without this file, students' submissions to `day2_p1_pi_extended` will
exit non-zero (FileNotFoundError on `sys.argv[1]`) and be graded as
"Code did not execute cleanly" — which is correct behavior, just not
useful pedagogy.
