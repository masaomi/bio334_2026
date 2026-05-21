

seq1 = "ATGC"   # First sequence
seq2 = "ATAT"   # Second sequence
seq3 = "ATGC"   # Third sequence

sequences = [seq1, seq2, seq3]  # Define a sequence list having three sequences

total_diff = 0  # initialize total_diff variable to count the total number of nucleotide differences
for i in range(0, len(sequences)):                      # Itelation to select the first sequence in combination
    for j in range(i+1, len(sequences)):                # Itelation to select the secont sequence in combination
        for k in range(0, len(sequences[i])):           # Itelation to select each element in the selected sequences
            if not sequences[i][k] == sequences[j][k]:  # Check if the selected elements are different
                total_diff += 1                         # Count up the number of different nucleotides

num_sequences = len(sequences)                          # The total number of sequences, i.e. 3
len_sequence = len(sequences[0])                        # The length of the sequence, i.e. 4
combination = num_sequences*(num_sequences-1)/2         # Calculate the number of combination, i.e. 4C2
PI = total_diff/combination                             # Calculate PI, nucleotide diversity (mean pairwise difference)
pi = total_diff/combination/len_sequence                # Calculate pi, nucleotide diversity (per site)
print("Sequences =", sequences)
print("Total differences =", total_diff)                # Show the total number of nucleotides
print("nC2 =", combination)                             # Show the number of combination
print("Length of sequence =", len_sequence)             # Show the length of sequence
print("Mean pairwise difference PI =", PI)              # Show the nucleotide diversity
print("pi = PI/(Length of sequence) =", pi)             # Show the nucleotide diversity


