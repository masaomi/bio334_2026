

import sys

sequences = []
f = open(sys.argv[1])
for line in f:
    if not line[0] == ">":
        sequences.append(line.rstrip())
f.close()

total_seg_sites = 0

#
# Implement a process here
#

print("total segregated sites =", total_seg_sites)  # Show the total number of segregated sites
