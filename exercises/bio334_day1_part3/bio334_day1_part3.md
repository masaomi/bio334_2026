# Day1 Part3


## Goal

* Understand the meaning of nested loop structure and you can compare more than 2 sequences

## Example1

* Double loop structure and two dimensional data set

Source code

```python
# List of Lists

lst1 = [0, 1]
lst2 = [2, 3]
lst = [lst1, lst2]
print(lst[0][0]) # => 0
print(lst[0][1]) # => 1
print(lst[1][0]) # => 2
print(lst[1][1]) # => 3
print("")

# List of Strings

str1 = "AT"
str2 = "GC"
lst = [str1, str2]
print(lst[0][0]) # => A
print(lst[0][1]) # => T
print(lst[1][0]) # => G
print(lst[1][1]) # => C
print("")

for i in range(0, 2):     # select string
    for j in range(0, 2): # select position
        print(lst[i][j])
```

Note
* Double loop structure is useful to access the elements of two dimensional dataset (like a table).

## Example2 

* Permutation and combination list

```python
lst = ["a", "b", "c", "d", "e"]    # Initialization of list

# Permutation list
print("permutations")
for i in range(0, len(lst)):       # Iteration of list with index, i becomes the first list index
    for j in range(0, len(lst)):   # inside loop of iteration, j becomes the second list index
        if not lst[i] == lst[j]    # except for that the selected elements are same
            print(lst[i], lst[j])  # show each element of two lists       
                                                                               
# Combination list                                                             
print("")                                                                        
print("combinations")                                                          
for i in range(0, len(lst)):        # First loop
    for j in range(i+1, len(lst)):  # Second loop, be careful of the start index
        print(lst[i], lst[j])       # show each element of two lists
```

Question
* How many times are the sets (of permutation and combination) printed out?

Note
* Please be careful to look at the start index in the range method
* The partial permutation is defined as the set of numbers to allow a different order, e.g. (1,2) and (2,1) are different in permutation
* The combination is defined as the set of numbers but it does not allow the different order, e.g. (1,2) and (2,1) are same in combination

## Exercise1

* Pair-wise comparison of 3 sequences (Just check if same or different?)

Template
```python
seq1 = "ATGC"   # First sequence
seq2 = "ATAT"   # Second sequence
seq3 = "ATGC"   # Third sequence

sequences = [seq1, seq2, seq3]  # Define a sequence list having three sequences

for i in range(0, len(sequences)):             # First loop to pick the first sequence
    for j in range(i+1, len(sequences)):       # Second loop to pick the second sequence
    #
    # Your code here
    #
```

Expected result
<pre>
$ python day1_3_exercise1.py
0 ATGC 1 ATAT	different
0 ATGC 2 ATGC	same
1 ATAT 2 ATGC	different
</pre>

## Exercise2

* Pair-wise comparison of 3 sequences and print the total number of different nucleotides at each position

```
seq1 = "ATGC"   # First sequence
seq2 = "ATAT"   # Second sequence
seq3 = "ATGC"   # Third sequence

sequences = [seq1, seq2, seq3]  # Define a sequence list having three sequences

total_same = 0  # Initialize a variable to count the total number of same nucleotides at the same position
total_diff = 0  # Initialize a variable to count the total number of different nucleotides at the same position
for i in range(0, len(sequences)):  # Iteralation to compare the sequences, the index i is used to select the first sentence
    for j in range(i+1, len(sequences)):    # Secont iteration, the index j is used to select the second sentence
        same = 0    # a variable to count the number of same nucleotides in each postion
        diff = 0
        print(i, sequences[i], j, sequences[j], end="\t")
        #
        # Your code here
        #

print("total same = %d" % total_same)
print("total diff = %d" % total_diff)
```

Hint
* This calculation needs 3 times nested loop structure

Expected result
<pre>
$ python day1_3_exercise2.py
0 ATGC 1 ATAT	same 2 diff 2
0 ATGC 2 ATGC	same 4 diff 0
1 ATAT 2 ATGC	same 2 diff 2
total same = 8
total diff = 4
</pre>

## Advanced Exercise 1: Calculating Nucleotide Diversity (π)


Given the following list of sequences:

```python
sequences = ['ATGC', 'ATAT', 'ATGC']
```

You should:

1. Compare all unique pairs (i.e., 0 vs 1, 0 vs 2, 1 vs 2)
2. Count the number of nucleotide differences at each position
3. Sum the total number of differences
4. Compute the number of combinations (`nC2`)
5. Calculate:

   * Mean pairwise difference
   * Nucleotide diversity π

**Expected Output**

<pre>
$ python day1_3_advanced1.py
Sequences = ['ATGC', 'ATAT', 'ATGC']
Total differences = 4
nC2 = 3.0
Length of sequence = 4
Mean pairwise difference PI = 1.3333333333333333
pi = PI/(Length of sequence) = 0.3333333333333333
</pre>

---

**Background**

In population genetics, **nucleotide diversity (π)** is a measure of how genetically different the sequences in a population are.
It is calculated as the **average number of nucleotide differences per site** between all possible pairs of DNA sequences.

**Concept**

Given:

* A list of **aligned DNA sequences** of equal length
* You compare **all possible pairs** of sequences
* For each pair, count how many **nucleotides are different** (i.e. mismatches) at each position
* Then calculate the **average number of differences per pair (π)**

---

### **Formula**

Let:

* *n* = number of sequences
* *L* = length of each sequence
* *D* = total number of differences across all pairs

Then:

* Number of pairs = *nC2* = `n * (n - 1) / 2`
* Mean pairwise difference = *π\_total* = `D / nC2`
* Nucleotide diversity π = `π_total / L`

**Hint**

* Use a **triple nested loop**:
  * Outer loop: compare all pairs
  * Inner loop: compare nucleotides at each position
* You can use `len(sequences)` for *n* and `len(sequences[0])` for *L*
* Use a counter variable to keep track of total mismatches


**Why This Is Important**

| Concept              | Application                                                           |
| -------------------- | --------------------------------------------------------------------- |
| Pairwise comparison  | Foundation for many bioinformatics analyses (e.g., distance matrices) |
| Nucleotide diversity | Important metric in evolutionary and population genetics              |
| Nested loops         | Reinforces structured iteration in Python                             |
| Abstract → Code      | Connects biological concepts with algorithmic thinking                |



