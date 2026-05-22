---
name: python_file_io_parsing
description: File I/O — FASTA/VCF parsing, sys.argv, and separation of data from code
layer: L1
version: "1.3"
tags:
  - python
  - file-io
  - fasta
  - vcf
  - parsing
  - teaching
  - bio334
---

# File I/O and Parsing for Bioinformatics

> Bioinformatics is fundamentally about processing files. Understanding file formats and the principle of separating data from code is more important than memorizing parsing syntax.

> **Scope**: This file covers **Python code patterns** for reading and parsing files. For format structure and rules (what makes a valid FASTA/VCF file), see `bioinformatics_file_formats`.

---

## 1. Why File I/O Matters

**The most important principle**: separate your data from your code.

- **Bad practice**: Hardcoding sequences into your script. Every data change requires editing code.
- **Good practice**: Reading data from a file. The same script works on any input file.

---

## 2. FASTA Format

```
>sequence_identifier optional description
ATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCG
>another_sequence
GCTAGCTAGCTAGCTA
```

**Rules**:
- Header line starts with `>`.
- All subsequent lines until the next `>` (or end of file) contain the sequence.
- Sequences are often split across multiple lines (60 or 80 characters per line).

**Critical understanding**: A FASTA file is not one-sequence-per-line. The multi-line nature means naive line-by-line processing gives fragments, not complete sequences.

---

## 3. Reading Files in Python

### Reading methods

| Method | Returns | When to use |
|--------|---------|-------------|
| `read()` | Entire file as one string | Small files |
| `readlines()` | List of lines | Line-by-line with random access |
| `for line in f` | One line at a time | Large files (memory efficient) |

### The `with` statement

```python
with open("data.fasta") as f:
    for line in f:
        # process each line
```

Always use `with` -- it automatically closes the file.

---

## 4. Command-line Arguments: sys.argv

```python
import sys
input_file = sys.argv[1]  # first argument after the script name
```

Running `python parse.py sequences.fasta` sets `sys.argv[1]` to `"sequences.fasta"`.

- `sys.argv[0]` -- the script name
- `sys.argv[1]` -- first user argument
- `sys.argv[2]` -- second user argument

**Common error**: Running `python parse.py` without arguments causes `IndexError: list index out of range` on `sys.argv[1]`. Always guard with:

```python
import sys
if len(sys.argv) < 2:
    print("Usage: python parse.py <input.fasta>")
    sys.exit(1)
input_file = sys.argv[1]
```

**In the web app**: The Args input field next to the Run button provides `sys.argv[1:]` values. Enter the filename there when running scripts that use `sys.argv`.

---

## 5. FASTA Parsing Algorithm

### Step-by-step logic

1. Initialize empty dictionary for results.
2. Initialize current sequence name as None.
3. For each line:
   - Strip whitespace.
   - Skip blank lines.
   - If starts with `>`: extract name, initialize empty sequence.
   - Otherwise: append to current sequence.
4. After all lines: dictionary contains all sequences.

### Conceptual structure

```python
sequences = {}
current_name = None

for line in file:
    line = line.strip()
    if not line:
        continue  # skip blank lines
    if line.startswith(">"):
        current_name = line[1:]
        sequences[current_name] = ""
    elif current_name is not None:  # only append if we've seen a header
        sequences[current_name] += line
```

This `elif current_name is not None` guard protects against malformed files that have sequence data before the first `>` header line. Using just `else:` would crash on such files.

**Verification**: Test with multi-line sequences. If parser returns sequences shorter than expected, it is not concatenating correctly.

---

## 6. VCF Format (Introduction)

### Key elements

- **Meta-information lines** start with `##` -- skip during parsing.
- **Header line** starts with `#CHROM` -- defines column names.
- **Data lines** are tab-separated.

### Important columns

| Column | Meaning | Example |
|--------|---------|---------|
| CHROM | Chromosome | `chr1` |
| POS | Position (1-based) | `1000` |
| REF | Reference allele | `A` |
| ALT | Alternative allele(s) | `G` |
| FORMAT | Genotype field format | `GT:DP` |
| Samples | Per-sample genotype data | `0/1:15` |

### Genotype notation

- `0/0` -- homozygous reference
- `0/1` -- heterozygous
- `1/1` -- homozygous alternative

**Critical**: VCF uses **1-based** coordinates; Python uses **0-based** indexing. VCF position 1000 = Python index 999.

---

## 7. The Agentic Approach to Parsing

1. **Understand the format** -- know the structure.
2. **Instruct AI precisely** -- not "parse this file" but specify the exact output data structure.
3. **Verify with known data** -- test with small files where you know the answer.

---

## 8. Teaching Checkpoints

**Q1**: AI code counts "number of sequences" by counting lines in a FASTA file. Why is this wrong?

> Expected: FASTA files have multiple lines per sequence. Count lines starting with `>` instead.

**Q2**: VCF position 500 shows REF=G, but `reference_seq[500]` gives T. What to check?

> Expected: Coordinate system mismatch. VCF is 1-based, Python is 0-based. Check `reference_seq[499]` instead.
