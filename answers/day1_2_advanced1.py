
seq1 = "ATGCATGCATGCATGCATATATGCATGC"   # Set a reference sequence
seq2 = "ATAT"                           # Set a target sequence

for i in range(0, len(seq1)):           # Search the target in the reference sequence
    print(f"{i}\t{seq1[i:i+4]}\t", end="") #f-string
    #print("%d\t%s\t" % (i, seq1[i:i+4]), end="") #python3
    #print "%d\t%s\t" % (i, seq1[i:i+4]), #python2
    if seq1[i:i+4] == seq2:             # the case of that the target sequence with the target is found in the reference
        print("Match")                  # Show Match 
    else:                               # the case of that the the target sequence is not found in the position
        print("Not match")




