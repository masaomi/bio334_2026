# Tajima's D (Summary)

## Definition
Neutrality test comparing two estimators of theta (= 4N*mu):
- pi (pairwise nucleotide diversity) -- sensitive to variant frequency
- theta_w (Watterson's estimator) -- counts segregating sites only

## Formula
```
D = (pi - theta_w) / sqrt(V(d))
theta_w = S / a_1,  where a_1 = Sum(1/i) for i=1..n-1
V(d) = e_1*S + e_2*S*(S-1)
```

## Interpretation
- D approx 0: neutral evolution, constant population
- D < 0: excess rare variants (expansion, positive selection, purifying selection)
- D > 0: excess intermediate-frequency variants (balancing selection, bottleneck, structure)

## Algorithm Steps
1. Count segregating sites S
2. Compute pi (average pairwise differences)
3. Compute theta_w = S / a_1
4. Compute d = pi - theta_w
5. Compute variance V(d) using Tajima's coefficients
6. D = d / sqrt(V(d))

## Common Mistakes
- Using S/L instead of S/a_1 for theta_w
- Mixing per-site and per-sequence normalization
- Assuming normal distribution (null is approximately beta)
- Interpreting D in isolation without other tests
- Over-interpreting with small sample sizes (n < 10)
