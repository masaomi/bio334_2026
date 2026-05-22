---
name: python_basics_for_bio
description: Python basics — minimum conceptual understanding for bioinformatics in the Agentic Coding era
layer: L1
version: "1.3"
tags:
  - python
  - basics
  - bioinformatics
  - data-structures
  - teaching
  - bio334
---

# Python Basics for Bioinformatics

> In the Agentic Coding era, the goal is not to memorize syntax but to **understand what code does** and **instruct AI precisely**.

---

## 1. Why Python for Bioinformatics

- **Readability**: Python reads close to English pseudocode. A biologist can look at `for gene in gene_list:` and understand what is happening.
- **Libraries**: BioPython for sequence analysis, pandas for tabular data, matplotlib/seaborn for visualization, scikit-learn for machine learning.
- **Community**: When you encounter a problem, someone has already asked and answered it.

In the agentic era, Python's readability is even more important: when an AI generates code, you need to **verify** it.

---

## 2. Essential Concepts

### Variables and Types

| Type | What it holds | Bioinformatics example |
|------|--------------|----------------------|
| `str` | Text | `"ATCGATCG"` -- a DNA sequence |
| `int` | Whole number | `42` -- a read count |
| `float` | Decimal number | `0.001` -- a p-value |
| `list` | Ordered collection | `["gene1", "gene2", "gene3"]` |
| `dict` | Key-value pairs | `{"gene1": "ATCG", "gene2": "GCTA"}` |
| `set` | Unique elements | `{"A", "T", "C", "G"}` |
| `tuple` | Immutable ordered collection | `("chr1", 1000, 2000)` |
| `bool` | True/False | `is_polymorphic = True` |
| `None` | Absence of value | `current_name = None` (no sequence being read yet) |

**Key insight**: A list preserves order and allows duplicates; a set contains only unique elements.

### Control Flow

- **if / elif / else**: Branching based on conditions.
- **for loop**: Doing something for every item in a collection.
- **while loop**: Repeating as long as a condition holds.

### String Operations

- **Indexing**: `seq[0]` gets the first character. Positions start at 0.
- **Slicing**: `seq[10:20]` extracts positions 10 through 19 (10 characters).
- `seq[0:3]` gives you three characters (the first codon), not four.

### String Methods

Strings have built-in methods that AI-generated code uses constantly:

- `.strip()` -- removes whitespace and newline characters from both ends
- `.startswith(">")` -- checks if a string begins with a specific prefix
- `.split("\t")` -- splits a string into a list at each tab character
- `.replace("_", " ")` -- replaces all occurrences of one substring with another
- `.upper()` / `.lower()` -- case conversion

These are essential for reading and verifying file-parsing code.

### List Comprehensions

```python
gc_counts = [seq.count("G") + seq.count("C") for seq in sequences]
```

You need to **read** these, because AI generates them frequently.

### Nested Loops

When comparing every item to every other item (e.g., pairwise sequence comparison):

```python
for i in range(len(sequences)):
    for j in range(i + 1, len(sequences)):
        # compare sequences[i] and sequences[j]
```

Why `i + 1`? If you compare Seq1 vs Seq2, you don't need to also compare Seq2 vs Seq1 — they are the same pair. Starting the inner loop at `i + 1` skips pairs you have already seen and avoids comparing a sequence with itself. This pattern produces exactly `n*(n-1)/2` unique pairs.

### Dictionary Building Pattern

Building a dictionary inside a loop (common in FASTA parsing):

```python
result = {}
for item in data:
    key = extract_key(item)
    result[key] = extract_value(item)
```

### The `import` Statement

`import` loads external functionality:

```python
import sys          # system utilities (e.g., sys.argv for command-line arguments)
from math import sqrt  # import a specific function
```

You do not need to memorize which modules exist -- AI knows them. But you need to recognize `import` lines when reading code.

---

## 3. Data Structures for Bioinformatics

### List -- Ordered Sequences
Maintains insertion order, allows duplicates. Use for: storing sequences from a FASTA file.

### Dictionary -- Key-Value Mapping
Maps unique keys to values. Fast lookup. Use for: gene name to sequence mapping, codon table.

### Set -- Unique Elements
Automatically removes duplicates. Supports union, intersection, difference. Use for: finding unique nucleotides at a position (SNP detection), comparing gene lists.

---

## 4. The "Agentic Minimum"

Even when AI writes 100% of your code, you must understand:

1. **What a for loop does**: Visits every item, one at a time, performs an action on each.
2. **What a function does**: Reusable, named computation with inputs and outputs.
3. **What indexing means**: `seq[i]` retrieves element at position i. Position 0 is first.
4. **Input/output flow**: Data flows in from files, gets transformed, flows out to files/screen.
5. **Debugging with print()**: Insert `print(variable_name)` to inspect values at any point in the code. This is the simplest and most effective way to understand what code is doing.

---

## 5. Teaching Checkpoints

**Q1**: You have 1000 gene names from RNA-seq and 500 known cancer genes. Which data structure for finding overlaps?

> Expected: A set -- for intersection of two collections of unique identifiers.

**Q2**: A script extracts the first 100 bases with `subseq = seq[1:101]`. Is there a problem?

> Expected: Yes -- this skips position 0 (the first base). Correct: `seq[0:100]` or `seq[:100]` (these are equivalent — omitting the start index defaults to 0).

**Q3**: You want AI to "calculate GC content of every sequence in a FASTA file." What key information does the AI need?

> Expected: (1) input file path and format, (2) definition of GC content, (3) desired output format, (4) output file path.
