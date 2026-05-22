# File I/O & Parsing (Summary)

## Core Principle
Separate data from code. Read from files, not hardcoded strings.

## FASTA Parsing Algorithm
1. Initialize empty dict, current_name = None
2. For each line: strip whitespace
3. If starts with `>`: new sequence name, init empty string
4. Else: append line to current sequence
5. Result: dict mapping names to concatenated sequences

## sys.argv for Command-line Arguments
- `sys.argv[0]` = script name
- `sys.argv[1]` = first argument (e.g., input filename)
- Makes scripts reusable across different input files

## File Reading Patterns
- `with open(f) as fh:` -- always use `with` for auto-close
- `for line in fh:` -- memory-efficient line iteration
- `.strip()` -- remove whitespace/newlines

## VCF Key Points
- Tab-separated, 1-based positions
- Skip `##` meta-lines, parse `#CHROM` header
- Genotypes: 0/0, 0/1, 1/1
- VCF POS -> Python index: subtract 1

## Common Mistakes
- Not concatenating multi-line FASTA sequences
- Counting lines instead of `>` headers for sequence count
- VCF 1-based vs Python 0-based coordinate mismatch
- Not stripping whitespace from parsed lines
