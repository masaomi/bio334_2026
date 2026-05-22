

import sys

def load_fasta(fasta):  
    sequences = []      

    f = open(fasta)     
    for line in f:      
        if not line[0] == ">":  
            sequences.append(line.rstrip()) 
    f.close()           
    return sequences    


def calc_pi(sequences):       
    total_diff = 0  
    for i in range(0, len(sequences)):                      
        for j in range(i+1, len(sequences)):                
            for k in range(0, len(sequences[i])):           
                if not sequences[i][k] == sequences[j][k]:  
                    total_diff += 1                         
    
    num_sequences = len(sequences)                          
    len_sequence = len(sequences[0])                        
    combination = num_sequences*(num_sequences-1)/2.0
    PI = total_diff/combination                             
    pi = total_diff/combination/len_sequence                
    return pi

sequences = load_fasta(sys.argv[1])
print("pi =", calc_pi(sequences))

