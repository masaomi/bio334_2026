def read_fasta(filename):
    with open(filename, 'r') as file:
        sequences = []
        sequence = ''
        for line in file:
            line = line.strip()
            if line.startswith('>'):
                if sequence:
                    sequences.append(sequence)
                    sequence = ''
            else:
                sequence += line
        if sequence:
            sequences.append(sequence)
    return sequences

def calculate_maf(alleles):
    allele_counts = {}
    for allele in alleles:
        if allele in allele_counts:
            allele_counts[allele] += 1
        else:
            allele_counts[allele] = 1
    total_alleles = sum(allele_counts.values())
    freqs = [count / total_alleles for count in allele_counts.values()]
    maf = min(freqs)
    return maf

def nucleotide_diversity(maf):
    p = 1 - maf
    q = maf
    pi = 2 * p * q
    return pi

def calculate_pi_for_multiple_sites(sequences):
    num_sites = len(sequences[0])
    total_pi = 0

    for site in range(num_sites):
        alleles = [seq[site] for seq in sequences]
        maf = calculate_maf(alleles)
        pi = nucleotide_diversity(maf)
        total_pi += pi
    
    mean_pi = total_pi / num_sites
    return mean_pi

def main(fasta_file):
    sequences = read_fasta(fasta_file)
    mean_pi = calculate_pi_for_multiple_sites(sequences)
    print(f"Mean Nucleotide Diversity (π): {mean_pi}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python nucleotide_diversity.py <fasta_file>")
    else:
        main(sys.argv[1])

