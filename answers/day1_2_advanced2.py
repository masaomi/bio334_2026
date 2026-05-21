
seq = "ATGCATGCATGCATGCATATATGCATGC"   # Set a reference sequence
print(seq)

rev = ""
for i in range(0, len(seq)):           # Search the target in the reference sequence
    j = len(seq) - i - 1
    if seq[j] == "A":             # the case of that the target sequence with the target is found in the reference
      rev += "T"
    elif seq[j] == "T":                               # the case of that the the target sequence is not found in the position
      rev += "A"
    elif seq[j] == "G":                               # the case of that the the target sequence is not found in the position
      rev += "C"
    elif seq[j] == "C":                               # the case of that the the target sequence is not found in the position
      rev += "G"
print(rev)


