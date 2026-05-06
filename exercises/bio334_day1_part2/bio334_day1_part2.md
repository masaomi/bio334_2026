# Day1 Part2

## Goal

* Understand String object and you can compare two nucleotide sequences

## Example1

* Compare two lists

Source code
```python:day1_2_example1.py
list1 = [1, 2, 3, 4, 5, 6]  # First list
list2 = [1, 2, 0, 4, 5, 0]  # Second list

for i in range(0, len(list1)):  # Iteration with the index of list1
    print("%s %s : " % (list1[i], list2[i]), end = "")
    if list1[i] == list2[i]:    # Comparison of each element at the same position
        print("True")           # In case of the two elements are same
    else:
        print("False")          # In case of the two elements are different
```

Result
<pre>
$ python day1_2_example1.py
1 1 : True
2 2 : True
3 0 : False
4 4 : True
5 5 : True
6 0 : False
</pre>

Note
* It is useful to use <code class="python">range</code> method with <code class="python">for</code> in the case of two lists comparison
* In the iteration process, each element of the two lists at the same position is compared
* If it is the same element (object), the <code class="python">if</code> condition becomes <code class="python">True</code>, otherwise becomes <code class="python">False</code>

## Exercise1

* Compare two nucleotide sequences and count the number of same and different nucleotides at each position.

Hint
* Each character in a String object can be accessed by index like a list element

For example
```python
string = "abc"
print(string[1]) # => b
```

Tempalate
```python
seq1 = "ATGCATGC"   # First string
seq2 = "ATGGATCC"   # Secont string

sequences = [seq1, seq2]    # List having two string objects

same = 0            # Initialization of the counter variable to count the total number of same elements at each position
diff = 0            # Initialization of the counter variable to count the total number of different elements at each position

# 
# Your code here
# 

print("same nucleotides : %d" % same)       # Show the total number of same characters
print("differnt nucleotides : %d" % diff)   # Show the total number of different characters
```

Expected result
<pre>
$ python day1_2_exercise1.py
A A : True
T T : True
G G : True
C G : False
A A : True
T T : True
G C : False
C C : True
same nucleotides : 6
differnt nucleotides : 2
</pre>

## Advanced Exercise 1: Searching a DNA Pattern in a Sequence (Mini-BLAST)

Write a program that:

* Uses the following reference sequence:

  ```
  ATGCATGCATGCATGCATATATGCATGC
  ```

* Searches for the query string `'ATAT'`
* Slides one base at a time
* Prints:

  * The position
  * The 4-letter substring starting at that position
  * Whether it matches the query (`Match` or `Not match`)

**Background**

In bioinformatics, tools like **BLAST** are used to find whether a short DNA sequence (called a *query*) appears in a longer DNA sequence (called a *reference*).

In this exercise, you will try to **simulate a simple version of this** using Python:

* Slide a window of 4 bases across the reference sequence
* At each position, compare the substring to the target (query)
* Print whether it matches or not

**Expected Output**

<pre>
$ python day1_2_advanced1.py
0	ATGC	Not match
1	TGCA	Not match
2	GCAT	Not match
3	CATG	Not match
4	ATGC	Not match
5	TGCA	Not match
6	GCAT	Not match
7	CATG	Not match
8	ATGC	Not match
9	TGCA	Not match
10	GCAT	Not match
11	CATG	Not match
12	ATGC	Not match
13	TGCA	Not match
14	GCAT	Not match
15	CATA	Not match
16	ATAT	Match
17	TATA	Not match
18	ATAT	Match
19	TATG	Not match
20	ATGC	Not match
21	TGCA	Not match
22	GCAT	Not match
23	CATG	Not match
24	ATGC	Not match
25	TGC	Not match
26	GC	Not match
27	C	Not match
</pre>

## Advanced Exercise 2: Making the Reverse Complement of a DNA Sequence

Write a Python program that:

1. Takes this sequence:

   ```
   ATGCATGCATGCATGCATATATGCATGC
   ```
2. Converts it to its **complement** using the rule:

   * A → T
   * T → A
   * G → C
   * C → G
3. Reverses the complemented string
4. Prints the original and reverse-complemented sequences

### **Background**

DNA consists of four bases:

* A (Adenine)
* T (Thymine)
* G (Guanine)
* C (Cytosine)

A base always pairs with its complement:

* A ↔ T
* G ↔ C

The **reverse complement** of a DNA strand is:

1. **Replace each base with its complement**
2. **Reverse the resulting string**

This is important in bioinformatics because DNA is double-stranded and often read in reverse-complement form.


**Expected Output**

<pre>
$ python day1_2_advanced2.py
ATGCATGCATGCATGCATATATGCATGC
GCATGCATATATGCATGCATGCATGCAT
</pre>
