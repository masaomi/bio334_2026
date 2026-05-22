
import sys      # import sys module to open and close methods

genome_size = 0                 # Initialize a variable to store the genome size
file = open(sys.argv[1])        # Open a fasta file, athal_genome.fa
for line in file:               # Read line by line using for statement
    if not line[0] == ">":      # Check the line beginning with '>', namely it checks if the line is the annotation or sequence
    #if not line.startswith(">"):
        genome_size += len(line.rstrip())   # If the line is sequence data, the length of the nucleotide string will be added to the variable. 
file.close()                                # Close the file

print("genome size =", genome_size, "bp")   # Show the genome_size

