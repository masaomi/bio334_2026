

seq1 = "ATGC"   # First sequence
seq2 = "ATAT"   # Second sequence
seq3 = "ATGC"   # Third sequence

sequences = [seq1, seq2, seq3]  # Define a sequence list having three sequences

total_same = 0  # Initialize a variable to count the total number of same nucleotides at the same position
total_diff = 0  # Initialize a variable to count the total number of different nucleotides at the same position
number_of_combination = 0
for i in range(0, len(sequences)):  # Iteralation to compare the sequences, the index i is used to select the first sentence
    for j in range(i+1, len(sequences)):    # Secont iteration, the index j is used to select the second sentence
        same = 0    # a variable to count the number of same nucleotides in each postion
        diff = 0
        number_of_combination += 1
        print(i, sequences[i], j, sequences[j], end="\t") #python3
        #print i, sequences[i], j, sequences[j], #python2
        for k in range(0, len(sequences[i])):   # Iteration to parse each position of the selected seuence
            if sequences[i][k] == sequences[j][k]:  # if each element of selected sequences is ssame
                same += 1                           # same variable incremted
                total_same += 1                     # total_same variable incremted 
            else:
                diff += 1                           # diff variable incremented
                total_diff += 1                     # total_diff variable incremented
        print("same %d diff %d" % (same, diff))
        
print("total same = %d" % total_same)
print("total diff = %d" % total_diff)
#print("number_of_combination = %d" % number_of_combination)
