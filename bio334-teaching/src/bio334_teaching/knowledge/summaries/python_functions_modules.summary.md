# Functions & Modules (Summary)

## Why Functions?
- **Reusability**: Write once, call many times
- **Abstraction**: Hide complexity behind clear interface
- **Testing**: Verify isolated units independently
- **DRY Principle**: Don't Repeat Yourself

## Function Structure
```python
def function_name(parameters) -> return_type:
    """Docstring: purpose, params, returns."""
    # implementation
    return result
```

## Refactoring Pattern
- Before: inline calculation in a script (works for 1 file)
- After: `read_fasta(filepath)` + `nucleotide_diversity(sequences)` (works for any file)

## Modules
- Save functions in a `.py` file (e.g., `bio_utils.py`)
- Import: `from bio_utils import read_fasta, nucleotide_diversity`
- BIO334 pattern: `exercise_module.py` grows throughout the course

## Agentic Perspective
Function signature = API contract = precise AI instruction:
- Vague: "Calculate diversity of my sequences"
- Precise: `nucleotide_diversity(sequences: list[str]) -> float`

## Common Mistakes
- Not separating reading from analysis into distinct functions
- Missing docstrings (especially in scientific code)
- Not returning values (procedure vs function)
