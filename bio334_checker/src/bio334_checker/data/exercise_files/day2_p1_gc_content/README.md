# Day 2, Part 1 Adv 1 — input data

This exercise expects `athal_genome.fa` (the *A. thaliana* genome
FASTA, ~120 MB uncompressed). It is the same file as
`day2_p1_pi_extended/athal_genome.fa`.

We do NOT bundle it inside the Python package because of size.

To activate this exercise, drop a copy or a symlink into this
directory:

```bash
# option A — symlink to a single shared copy
ln -s /var/lib/bio334/athal_genome.fa \
  src/bio334_checker/data/exercise_files/day2_p1_gc_content/athal_genome.fa

# option B — same gunzipped copy as Ex 1
gunzip -c /path/to/athal_genome.fa.gz > \
  src/bio334_checker/data/exercise_files/day2_p1_gc_content/athal_genome.fa
```

Without this file, submissions to `day2_p1_gc_content` will exit
non-zero (FileNotFoundError on `sys.argv[1]`) and be graded as
"Code did not execute cleanly".
