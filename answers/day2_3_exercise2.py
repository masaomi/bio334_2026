

import sys                  # Import sys module

def load_fasta(fasta):      # Define load_fasta method, fasta is an argument data file
    sequences = []          # Initialize seuqnces list

    f = open(fasta)         # Open a fasta file
    for line in f:          # Read line by line from the fasta file
        if not line[0] == ">": # Skip annotation lines
            sequences.append(line.rstrip()) # keep sequence data in sequences list
    f.close()               # Close the file 
    return sequences        # Return the sequences list

def count_seg_sites(sequences):             # Define a method to count total number of segregating sites from sequences list object
    total_seg_sites = 0                     # Initialize a variable to keep the total number ofsegregating sites
    for i in range(0, len(sequences[0])):   # Iteration of selecting a postion
        alleles = set()                     # Distinct nucleotides at this position
        for seq in sequences:               # Itelation of selecting a sequence
            alleles.add(seq[i])             # Keep the nucleotide in alleles set
        if len(alleles) > 1:                # Check if it is segregating sites or not
            total_seg_sites += 1            # If it is segregating, count up the variable
    return total_seg_sites                  # Return the total number of segregaed sites

sequences = load_fasta(sys.argv[1])                 # Call load_fasta method with a fasta file path and load sequence data
total_seg_sites = count_seg_sites(sequences)        # Calculate the total number of segregating sites
print("Total segregating sites =", total_seg_sites)  # Show the result

