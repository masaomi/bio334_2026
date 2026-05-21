
seq1 = "ATGC"   # First sequence
seq2 = "ATAT"   # Second sequence
seq3 = "ATGC"   # Third sequence

sequences = [seq1, seq2, seq3]  # Define a sequence list having three sequences

number_of_combination = 0
for i in range(0, len(sequences)):              # First loop to pick the first sequence
    for j in range(i+1, len(sequences)):        # Second loop to pick the second sequence
        number_of_combination += 1
        print(i, sequences[i], j, sequences[j], end="\t") #python3
        #print i, sequences[i], j, sequences[j], #python2
        if sequences[i] == sequences[j]:        # In the case that the selected two sequences are same
            print("same")
        else:                                   # In the case of different
            print("different")
#print(number_of_combination)
