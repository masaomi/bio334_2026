

import sys
import math

sequences = []
f = open(sys.argv[1])
for line in f:
    if not line[0] == ">":
        sequences.append(line.rstrip())
f.close()

total_diff = 0
for i in range(0, len(sequences)):
    for j in range(i+1, len(sequences)):
        for k in range(0, len(sequences[i])):
            if not sequences[i][k] == sequences[j][k]:
                total_diff += 1

total_seg_sites = 0
for i in range(0, len(sequences[0])):
    alleles = []
    for seq in sequences:
        alleles.append(seq[i])
    if len(set(alleles)) > 1:
        total_seg_sites += 1

num_sequences = len(sequences)
len_sequence = len(sequences[0])
combination = num_sequences*(num_sequences-1)/2.0
pi = total_diff/combination/len_sequence
sum_ = sum([1.0/i for i in range(1, num_sequences)])
s = float(total_seg_sites)/len_sequence
estimated_pi = s/sum_ # theata
d = pi - estimated_pi
PI = pi*len_sequence
dd = PI - total_seg_sites/sum_
print("Total differences =", total_diff)
print("nC2 =", combination)
print("Length of sequence =", len_sequence)
print("Nucleotide diversity pi =", pi)
print("Pair-wise difference PI =", PI)
print("Number of SNP sites (total segregating sites) S =", total_seg_sites)
print("Frequency of SNP sites s = S/sequence_length =", s)
print("sum_{i=1}^{n-1}(1/i) =", sum_)
print("estimated pi = s/sum(1/i) =", estimated_pi)

a1 = 0.0
a2 = 0.0
b1 = 0.0
b2 = 0.0
c1 = 0.0
c2 = 0.0
e1 = 0.0
e2 = 0.0

n = num_sequences
ss = total_seg_sites
for i in range(1, n):
    a1 += 1.0/i
    a2 += 1.0/(i*i)
b1 = (n+1.0)/(3.0*(n-1))
b2 = (2.0*(n*n+n+3))/(9.0*n*(n-1))
c1 = b1 - 1.0/a1
c2 = b2-(n+2)/(a1*n)+a2/(a1*a1)
e1 = c1/a1
e2 = c2/(a1*a1+a2)
var_d = e1*ss+e2*ss*(ss-1.0)
print("d = pi - estimated_pi =", d)
# Guard against n=2 / S=0 cases where var_d would be 0 and Tajima's D
# is undefined (no variance to normalise by). Avoids a silent
# divide-by-zero on degenerate input.
if n < 2 or ss == 0 or var_d <= 0:
    print("Tajima's D= nan (undefined for n<2 or S=0)")
else:
    td = dd/math.sqrt(var_d)
    print("Tajima's D=", td)




