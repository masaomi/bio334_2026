---
name: python_functions_modules
description: Functions and modules — reusability, abstraction, and modularization patterns
layer: L1
version: "1.3"
tags:
  - python
  - functions
  - modules
  - abstraction
  - reusability
  - teaching
  - bio334
---

# Python Functions and Modules

> **Scope**: This file covers function definition, module organization, and code reuse. For the actual FASTA parsing implementation used in `read_fasta()`, see `python_file_io_parsing`. For batch application of functions to many files, see `python_batch_processing`.

## 1. Why Functions?

Functions are the fundamental unit of code organization:

- **Reusability**: Write once, call many times.
- **Abstraction**: Hide complexity behind a clear interface.
- **Testing**: Isolated units can be verified independently.

### The DRY Principle: Don't Repeat Yourself

If you find yourself copying and pasting the same block of code, that block belongs in a function.

### Functions as the Unit of "Instruction"

In the agentic coding era, a function is the natural unit of instruction. When you say "calculate nucleotide diversity," you are describing a function. The clearer the function, the clearer the instruction.

---

## 2. Function Anatomy

```python
def nucleotide_diversity(sequences):
    """
    Calculate nucleotide diversity (pi) for a list of DNA sequences.

    Parameters:
        sequences (list of str): Aligned DNA sequences of equal length.

    Returns:
        float: Nucleotide diversity value.
    """
    n = len(sequences)
    if n < 2:
        return 0.0
    length = len(sequences[0])
    total_diff = 0
    num_comparisons = 0

    for i in range(n):
        for j in range(i + 1, n):
            # zip() pairs up characters at each position; sum() counts mismatches
            differences = sum(1 for a, b in zip(sequences[i], sequences[j]) if a != b)
            total_diff += differences
            num_comparisons += 1

    if num_comparisons == 0:
        return 0.0

    pi = total_diff / (num_comparisons * length)
    return pi
```

Four key parts:
- **`def`**: Declares the function and its name.
- **Parameters**: The inputs the function requires.
- **Docstring**: Description of purpose, parameters, and return value.
- **`return`**: The output.

---

## 3. From Script to Function

### Before: Inline Calculation
A script that calculates diversity directly -- works for one file, but what about 50 genes?

### After: Refactored into Functions
```python
def read_fasta(filepath):
    """Read a FASTA file and return a list of sequences."""
    # ... implementation ...

def nucleotide_diversity(sequences):
    """Calculate nucleotide diversity (pi)."""
    # ... implementation ...

# Now the main script is two lines:
seqs = read_fasta("gene1.fa")
print(f"Pi = {nucleotide_diversity(seqs)}")
```

The logic is the same. The structure is fundamentally better.

---

## 4. Modules -- Organizing Functions into Reusable Files

### Creating a Module

Save functions in a file called `bio_utils.py`:

```python
# bio_utils.py
def read_fasta(filepath):
    ...

def nucleotide_diversity(sequences):
    ...
```

### Importing a Module

```python
# Pattern 1: Import the whole module
import bio_utils
seqs = bio_utils.read_fasta("gene1.fa")

# Pattern 2: Import specific functions (recommended for BIO334)
from bio_utils import read_fasta, nucleotide_diversity

# Pattern 3: Import with alias
import bio_utils as bu
```

For this course, **Pattern 2** is recommended — it makes clear exactly which functions you are using.

### The exercise_module.py Pattern

In BIO334, students create an `exercise_module.py` file that grows throughout the course. Each exercise adds new functions; later exercises import earlier ones. This mirrors real-world scientific computing.

---

## 5. The Agentic Perspective -- Functions as API Contracts

A function signature is an **API contract**. When you tell an AI:

> "I need a function that takes a list of DNA sequences and returns nucleotide diversity (pi)"

You have specified input, output, and behavior. This is sufficient for AI to generate a correct implementation.

- **Without function thinking**: "Calculate the diversity of my sequences" -- vague.
- **With function thinking**: "Write `nucleotide_diversity(sequences: list[str]) -> float`" -- precise, testable.

The ability to decompose a problem into well-defined functions is the core skill of the Instruction Literacy layer.

---

## 6. Teaching Checkpoints

**Q1**: You have a script that reads a FASTA file and counts GC content inline. What function(s) would you create?

*Expected*: At minimum, `read_fasta(filepath) -> list[str]` and `gc_content(sequence) -> float`. Reading and analysis are separate concerns.

**Q2**: You have `read_fasta()` and `nucleotide_diversity()` in your exercise script. A classmate needs them. What do you do?

*Expected*: Place the functions in a module (e.g., `bio_utils.py`) and have the classmate import it.
