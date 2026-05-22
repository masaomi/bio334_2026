

import sys                                  # import sys module for open/close methods

sequences = []                              # Initialize a list to store sequence data
f = open(sys.argv[1])                       # Open input.fa 
for line in f:                              # Read line by lne from input.fa
    if not line[0] == ">":                  # Skip annotation line
        sequences.append(line.rstrip())     # Store the sequence data in sequences list object
f.close()                                   # End of file IO process

total_seg_sites = 0                         # Initialize a variable to store the total number of segregating sites
for i in range(0, len(sequences[0])):       # Iteration for checking each position  of the sequences
    alleles = []                            # Initialize a list to keep alleles at the position, i
    for seq in sequences:                   # Iteration to select a sequence
        alleles.append(seq[i])              # keep the nucleotide at the position, i
    print(sorted(set(alleles)), end="\t")   # python3  
    if len(set(alleles)) > 1:               # check if it is segerated or not
        print("segregating")
        total_seg_sites += 1                # count up the number of segregating sites
    else:
        print("not segregating")

print("Total segregating sites =", total_seg_sites)  # Show the total number of segregating sites
