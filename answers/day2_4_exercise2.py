

import sys
import math

def load_fasta(fasta):
    sequences = []

    f = open(fasta)
    for line in f:
        if not line[0] == ">":
            sequences.append(line.rstrip())
    f.close()
    return sequences

def count_diff(seq1, seq2):
    diff = 0
    for i in range(0, len(seq1)):
        if not seq1[i] == seq2[i]:
            diff += 1
    return diff

def count_total_diff(sequences):
    total_diff = 0
    for i in range(0, len(sequences)):
        for j in range(i+1, len(sequences)):
            total_diff += count_diff(sequences[i], sequences[j])
    return total_diff



def count_seg_sites(sequences):
    total_seg_sites = 0
    for i in range(0, len(sequences[0])):
        alleles = []
        for seq in sequences:
            alleles.append(seq[i])
        if len(set(alleles)) > 1:
            total_seg_sites += 1
    return total_seg_sites

def nucleotide_diversity(sequences):
    num_sequences = len(sequences)
    len_sequence = len(sequences[0])
    combination = num_sequences*(num_sequences-1)/2.0
    total_diff = count_total_diff(sequences) 
    pi = total_diff/combination/len_sequence
    return pi

def tajimas_d(sequences):
    num_sequences = len(sequences)
    len_sequence = len(sequences[0])
    pi = nucleotide_diversity(sequences)
    total_seg_sites = count_seg_sites(sequences)
    sum_ = sum([1.0/i for i in range(1, num_sequences)])
    s = total_seg_sites/len_sequence
    estimated_pi = s/sum_
    d = pi - estimated_pi
    PI = pi*len_sequence
    dd = PI - total_seg_sites/sum_

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
    # Guard against n=2 / S=0 cases where var_d would be 0 and Tajima's
    # D is undefined. Returning nan rather than dividing by zero is the
    # textbook-recommended behaviour.
    if n < 2 or ss == 0 or var_d <= 0:
        return float('nan')
    td = dd/math.sqrt(var_d)
    return td


sequences = load_fasta(sys.argv[1])
print("Tajima's D=", tajimas_d(sequences))




