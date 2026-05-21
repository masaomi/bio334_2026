
'''
nPr = n * (n-1) * (n-2) * ... * (n-r+1) = n! / (n-r)!
nCr = nPr / r! = n! / ((n-r)! * r!)
'''

import math

n = 5
r = 2

fact_n = 1.0
for x in range(1, n+1):
    fact_n *= x

fact_n_r = 1.0
for x in range(1, n-r+1):
    fact_n_r *= x

fact_r = 1.0
for x in range(1, r+1):
    fact_r *= x

p = fact_n / fact_n_r
print("%dP%d = %f" % (n, r, p))

c = fact_n / (fact_n_r * fact_r)
print("%dC%d = %f" % (n, r, c))

#p = math.factorial(n) / math.factorial(n-r)
#print("%dP%d = %f" % (n, r, p))

#c = math.factorial(n) / (math.factorial(n-r) * math.factorial(r))
#print("%dC%d = %f" % (n, r, c))
