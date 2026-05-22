# Bioinformatics File Formats (Summary)

## FASTA
- Header line starts with `>`
- Sequence may span multiple lines (must concatenate)
- Multi-FASTA: one file, many sequences

### Parsing pitfalls
- Forgetting to strip newlines from sequence lines
- Not concatenating multi-line sequences
- Mixed case (normalize before comparison)

## VCF (Variant Call Format)
- Meta lines: `##` prefix (skip)
- Header: `#CHROM POS ID REF ALT QUAL FILTER INFO FORMAT samples...`
- Data: tab-separated, one row per variant

### Key columns
- POS: 1-based position (Python index = POS - 1)
- REF/ALT: reference and alternate alleles
- Genotypes: 0/0 (hom ref), 0/1 (het), 1/1 (hom alt)

## FASTA vs VCF
- FASTA stores full sequences: O(N*L)
- VCF stores differences only: much more compact
- Given reference + VCF, full sequences are reconstructable

## Common Mistakes
- Not handling multi-line FASTA sequences
- VCF 1-based vs Python 0-based coordinate mismatch
- Treating gaps/N as regular nucleotides
