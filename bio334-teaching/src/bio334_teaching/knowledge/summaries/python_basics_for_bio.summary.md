# Python Basics for Bioinformatics (Summary)

## Core Types
| Type | Use case |
|------|----------|
| str | DNA sequences |
| int | Read counts |
| float | p-values, diversity scores |
| list | Ordered collection (sequences from FASTA) |
| dict | Key-value mapping (gene name -> sequence) |
| set | Unique elements (SNP detection, gene list overlap) |

## Control Flow
- `if/elif/else`: branching on conditions
- `for` loop: iterate over collection
- `while` loop: repeat while condition true

## Key Concepts
- **Indexing**: 0-based. `seq[0]` is first character.
- **Slicing**: `seq[0:3]` = 3 characters (positions 0,1,2).
- **List comprehension**: `[f(x) for x in items]` -- read these, AI generates them.

## Agentic Minimum (must understand even if AI writes code)
1. What a for loop does
2. What a function does
3. What indexing means (0-based!)
4. Input/output flow (files in -> transform -> files out)

## Common Mistakes
- Off-by-one errors with 0-based indexing
- Confusing list (ordered, duplicates) with set (unique)
- Not specifying input format precisely when instructing AI
