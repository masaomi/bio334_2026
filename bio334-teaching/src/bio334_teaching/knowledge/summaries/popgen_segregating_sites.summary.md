# Segregating Sites & theta_w (Summary)

## Definition
A segregating site is a position where at least two different nucleotides are observed across sampled sequences. S = total count of segregating sites.

## Watterson's Estimator
```
theta_w = S / a_n
a_n = Sum(1/i) for i = 1 to n-1  (harmonic number)
```
Per-site: theta_w / L

## Detection Algorithm
```
S = 0
for each position j:
    nucleotides = set(seq[j] for seq in alignment)
    if len(nucleotides) > 1:
        S += 1
```
- Use Python `set()` for uniqueness check
- Handle gaps/N characters explicitly
- Time complexity: O(n * L)

## Connection to Tajima's D
- theta_w sensitive to rare variants (singletons)
- pi sensitive to intermediate-frequency variants
- Under neutrality: E[theta_w] = E[pi] = theta
- D = (pi - theta_w) / sqrt(Var)

## Common Mistakes
- Forgetting the harmonic number normalization
- Not handling gap characters
- Confusing S (count) with S/L (rate)
