
seq1 = "ATGCATGC"   # First string
seq2 = "ATGGATCC"   # Secont string

sequences = [seq1, seq2]    # List having two string objects

same = 0            # Initialization of the counter variable to count the total number of same elements at each position
diff = 0            # Initialization of the counter variable to count the total number of different elements at each position
for i in range(0, len(sequences[0])):   # Iteration to compare each string
    print("%s %s : " % (sequences[0][i], sequences[1][i]), end = "") #python3
    #print "%s %s : " % (sequences[0][i], sequences[1][i]), #python2
    if seq1[i] == seq2[i]:  # same case
        print("True")
        same += 1           # Count the same variable up
    else:                   # different case
        print("False")
        diff += 1           # Count the diff variable up

print("same nucleotides : %d" % same)       # Show the total number of same characters
print("differnt nucleotides : %d" % diff)   # Show the total number of different characters  


