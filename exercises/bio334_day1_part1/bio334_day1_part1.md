# Day1 Part1

## Goal

* Understand how to calculate the sum of a list through reviewing Python grammar

## Example1

* Calculate the sum of list

Source code
```python
list1 = [1, 2, 3, 4, 5, 6]  # initialization of a list
total = 0                   # initialization of total variable
for i in list1:             # iteration of each element of the list
    total += i              # add the element to the total variable
print("total =", total)     # show the result

total = sum(range(1, 7))    # simple implementation
print("total = %d" % total) # show in a different way
```

How to execute
* After making a text file (source code), e.g. ex1.py, by using a text editor, you can type the following command on the terminal.

```bash
$ python3 ex1.py
total = 21
total = 21
```

Note
* Please use `python3` explicitly, otherwise *Python version 2* will be used
* list is defined as a set of data (object) with []
* `for var in list`: can take each element iteratively and assign the element to _var_
* <code class="python">sum</code> is a method to calculate the sum of list elements, but the element should be numerical value when you apply <code class="python">sum</code> method to <code class="python">list</code> object
* <code class="python">range(start, end)</code> generates list of consecutive numbers from _start_ to _(end - 1)_
* <code class="python">total += i </code> can be replaced by <code class="python">total = total + i </code>
* One of the important tips here is the combination of <code class="python">list</code> and <code class="python">for</code> in order to process each element in a list, so that it sums all the elements in the list here, but this concept is applicable to other algorithms.

## Exercise1

* Calculate mean of list elements

Expected result
<pre><code>
$ python day1_1_exercise1.py
list =  [1, 2, 3, 4, 5, 6]
mean = 3.5</code>
</pre>

### Exercise2

* Calculate standard deviation of list elements

Hint
* In order to calculate the square root, the following processes are needed:
  1. import math
  1. call math.sqrt() method


For example
<pre>
import math
print(math.sqrt(2)) # => 1.4142135623730951
</pre>


Expected result
<pre>
$ python day1_1_exercise2.py
list =  [1, 2, 3, 4, 5, 6]
sd = 1.707825
</pre>

## Advanced exercise1 (you may need to use AI)

Implement a Python program that:

1. Calculates **nPr** and **nCr** given `n = 5` and `r = 2`
2. Displays the result in the following format:

```bash
$ python day1_1_advanced1.py
5P2 = 20.000000
5C2 = 10.000000
```

**Background Explanation**

In mathematics, when selecting a number of elements from a group, the order may or may not matter:

* **Permutation** is used when the **order matters**.

  Example: Selecting 2 people from 5 to assign to two specific roles → (A, B) and (B, A) are different.

* **Combination** is used when the **order does not matter**.

  Example: Selecting 2 people from 5 to form a team → (A, B) and (B, A) are considered the same.

The formulas are:

* **Permutation**:

  $${}_nP_r = \frac{n!}{(n - r)!}$$

* **Combination**:

  $${}_nC_r = \frac{n!}{r!(n - r)!}$$

Where `!` means factorial (e.g. `5! = 5 × 4 × 3 × 2 × 1 = 120`)

Hint
* You can use `float()` in print to ensure decimal formatting (e.g. `%.6f`)


## Advanced exercise2 (you may need to use AI)

Simulating Sampling Bias and Estimating Mean & Variance

You are given a **synthetic population** represented as a list of integers from 1 to 1000 (you can use `range(1, 1001)`). This represents a **population of expression levels**, for example.

1. **Calculate the true mean and variance** of the population.
2. Randomly draw 100 samples (size = 10) from the population (with replacement), and:

   * Calculate the mean and variance for each sample
   * Store the sample means in a list
3. Calculate the **average of the sample means**
4. Compare:

   * True population mean vs. average of sample means
   * True variance vs. average of sample variances

Expected Output (example)

```
$ python day1_1_advanced2.py
Population mean = 500.5
Population variance = 83333.25
Average sample mean = 501.13
Average sample variance = 83921.82
```

Hints

* You can use `random.choices()` to draw a sample **with replacement**
* You can use `import statistics` for `mean()` and `variance()`
* You can use a loop to repeat sampling 100 times
