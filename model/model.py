import numpy as np
import pandas as pd

def linear_function(x, w):
  return w[0] + w[1] * x

# number of data records used to train
NO_VALUES = 11
# learning rate in gradient descent
LEARNING_RATE = 0.001
# number of learning iterations
EPOCHS = 1000
# interval at which training progress is printed
VERBOSE = EPOCHS / 10

# read data from the imported csv file and drop NaN values
data = pd.read_csv("./traffic_data.csv").dropna().values

# only get a subset data in the dataset
data = data[:NO_VALUES]

x = data[:, 0].reshape(-1, 1)
y = data[:, 1].reshape(-1, 1)

# standardize x
x_mean = np.mean(x, axis=0)
x_std = np.std(x, axis=0)
x = (x - x_mean) / x_std

# get number of records in dataset
N = data.shape[0]

# add a column of ones on the left of the old x
x = np.hstack((np.ones((N, 1)), x))

# create a w matrix with two initial values w_0=0 and w_1=1
w = np.array([0., 1.]).reshape(-1, 1)

cost = np.zeros((EPOCHS, 1))
for i in range(EPOCHS):
  r = x @ w - y

  # get the most exact w_0
  w[0] -= LEARNING_RATE * np.sum(r)
  # get the most exact w_1
  w[1] -= LEARNING_RATE * np.sum(r * x[:,1].reshape(-1, 1))

  cost[i] = np.sum(r ** 2) / (2 * N)
  if not i % VERBOSE:
    print("Epoch: ", i, " Cost: ", cost[i])

# save weights to a *.npy file
np.save('weights.npy', w)