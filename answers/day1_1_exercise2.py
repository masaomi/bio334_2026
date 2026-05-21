import math

list1 = [1, 2, 3, 4, 5, 6]
avg = sum(list1)/len(list1)
var = 0.0
for i in list1:
    var += (i - avg)**2
var /= len(list1)
#var /= len(list1)-1 #unbiased std
sd = math.sqrt(var)
print("list = ", list1)
print("sd = %f" % sd)

#import statistics
#print(statistics.stdev(list1))
#print(statistics.pstdev(list1))


