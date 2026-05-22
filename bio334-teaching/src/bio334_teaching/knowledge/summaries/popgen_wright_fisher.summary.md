# Wright-Fisher Model (Summary)

## Definition
Fundamental population genetics simulation modeling allele transmission as random sampling with replacement.

## Assumptions
- Haploid population, constant size N
- No selection (neutral), point mutations only at rate mu
- Expected diversity at equilibrium: theta = 2N*mu (haploid)

## Algorithm
1. Initialize N identical sequences of length L
2. Each generation:
   - Draw N sequences with replacement (drift)
   - Apply point mutations at rate mu per site (mutation)
3. Track S, pi, Tajima's D over T generations

## Key Scenarios
| Scenario | pi | Tajima's D |
|----------|-----|-----------|
| No mutation | -> 0 | -> negative/undefined |
| Constant N + mutation | stabilizes at 2N*mu | fluctuates around 0 |
| Population expansion | low relative to S | < 0 (excess rare variants) |
| Bottleneck | high relative to S | > 0 (excess intermediate variants) |
| Selective sweep | reduced | < 0 |

## Common Mistakes
- Forgetting sampling is WITH replacement
- Confusing haploid (2N*mu) and diploid (4N*mu) expectations
- Not running enough generations to reach equilibrium
