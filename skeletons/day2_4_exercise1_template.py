import sys      # Import sys module for file IO


# Load a FASTA file
sequences = []

#
# Your code here
#     

# Calculate the total number of different nucleotides
total_diff = 0

#
# Your code here
#

# Calculate the total number of segregating sites
total_seg_sites = 0

#
# Your code here
#

# Calculate pi
num_sequences = len(sequences)
len_sequence = len(sequences[0])
combination = num_sequences*(num_sequences-1)/2.0
pi = total_diff/combination/len_sequence
sum_ = sum([1.0/i for i in range(1, num_sequences)])
s = float(total_seg_sites)/len_sequence
estimated_pi = s/sum_
d = pi - estimated_pi
PI = pi*len_sequence
dd = PI - total_seg_sites/sum_
print("Total differences =", total_diff)
print("nC2 =", combination)
print("Lenght of sequence =", len_sequence)
print("Nucleotide diversity pi =", pi)
print("Pair-wise difference PI =", PI)
print("Number of SNP sites (total segregating sites) S =", total_seg_sites)
print("Frequency of SNP sites s = S/sequence_length =", s)
print("sum_{i=1}^{n-1}(1/i) =", sum_)
print("estimated pi = s/sum(1/i) =", estimated_pi)
print("d = pi - estimated_pi =", d)

# Calculate the standard deviation of d and Tajima's D

#
# Your code here
#

print("Tajima's D=", td)


