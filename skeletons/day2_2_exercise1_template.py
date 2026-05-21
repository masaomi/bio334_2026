

import sys


sequences = []
file = open(sys.argv[1])
for line in file:
    if not line[0] == ">":
        sequences.append(line.rstrip())
file.close()


total_diff = 0

#
# Implement here
#

num_sequences = len(sequences)
len_sequence = len(sequences[0])
combination = num_sequences*(num_sequences-1)/2
pi = total_diff/combination/len_sequence
print("total differences =", total_diff)
print("nC2 =", combination)
print("Lenght of sequence =", len_sequence)
print("pi =", pi)


