import random

# 1. Create a population of integers from 1 to 1000
population = list(range(1, 1001))

# Function to calculate mean
def calc_mean(data):
    return sum(data) / len(data)

# Function to calculate variance
def calc_variance(data):
    mean = calc_mean(data)
    return sum((x - mean) ** 2 for x in data) / len(data)

# 2. Calculate population mean and variance
pop_mean = calc_mean(population)
pop_variance = calc_variance(population)

# 3. Draw 100 random samples (size 10), calculate sample means and variances
sample_size = 10
num_samples = 100

sample_means = []
sample_variances = []

for _ in range(num_samples):
    sample = random.choices(population, k=sample_size)
    sample_mean = calc_mean(sample)
    sample_variance = calc_variance(sample)
    sample_means.append(sample_mean)
    sample_variances.append(sample_variance)

# 4. Calculate average of sample means and variances
avg_sample_mean = calc_mean(sample_means)
avg_sample_variance = calc_mean(sample_variances)

# 5. Print results
print("Population mean = %.2f" % pop_mean)
print("Population variance = %.2f" % pop_variance)
print("Average sample mean = %.2f" % avg_sample_mean)
print("Average sample variance = %.2f" % avg_sample_variance)

