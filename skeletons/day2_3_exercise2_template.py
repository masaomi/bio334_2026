

import sys

def load_fasta(fasta):
    sequences = []

    #
    # Your code here
    #

    return sequences

def count_seg_sites(sequences):
    total_seg_sites = 0

    #
    # Your code here
    #

    return total_seg_sites

sequences = load_fasta(sys.argv[1])
total_seg_sites = count_seg_sites(sequences)
print("Total segregating sites =", total_seg_sites)

