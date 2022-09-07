import torch
import numpy as np

from torch import nn
from torch.utils.data import DataLoader
from torchvision.transforms import ToTensor
from torchvision import datasets
from skorch import NeuralNetClassifier
from sklearn.model_selection import train_test_split
from modAL.models import ActiveLearner

device = "cuda" if torch.cuda.is_available() else "cpu"

# build class for the skorch API
class Torch_Model(nn.Module):
    def __init__(self,):
        super(Torch_Model, self).__init__()
        self.convs = nn.Sequential(
                                nn.Conv2d(1,32,3),
                                nn.ReLU(),
                                nn.Conv2d(32,64,3),
                                nn.ReLU(),
                                nn.MaxPool2d(2),
                                nn.Dropout(0.25)
        )
        self.fcs = nn.Sequential(
                                nn.Linear(12*12*64,128),
                                nn.ReLU(),
                                nn.Dropout(0.5),
                                nn.Linear(128,10),
        )

    def forward(self, x):
        out = x
        out = self.convs(out)
        out = out.view(-1,12*12*64)
        out = self.fcs(out)
        return out


# create the classifier
classifier = NeuralNetClassifier(Torch_Model,
                                 # max_epochs=100,
                                 criterion=nn.CrossEntropyLoss,
                                 optimizer=torch.optim.Adam,
                                 train_split=None,
                                 verbose=1,
                                 device=device)
dataroot = '../data/'
batch_size = 60000

dataloader = DataLoader(
    datasets.MNIST(root=dataroot, download=True, transform=ToTensor()),
    batch_size=batch_size, shuffle=True)

X_train, X_test, y_train, y_test = train_test_split(dataloader, test_size=0.2, random_state=42)

X, y = next(iter(dataloader))
X = X.detach().cpu().numpy()
y = y.detach().cpu().numpy()

# read training data
X_train, X_test, y_train, y_test = X[:50000], X[50000:], y[:50000], y[50000:]
X_train = X_train.reshape(50000, 1, 28, 28)
X_test = X_test.reshape(10000, 1, 28, 28)

# assemble initial data
n_initial = 1000
initial_idx = np.random.choice(range(len(X_train)), size=n_initial, replace=False)
X_initial = X_train[initial_idx]
y_initial = y_train[initial_idx]

# generate the pool
# remove the initial data from the training dataset
X_pool = np.delete(X_train, initial_idx, axis=0)[:5000]
y_pool = np.delete(y_train, initial_idx, axis=0)[:5000]

# initialize ActiveLearner
learner = ActiveLearner(
    estimator=classifier,
    X_training=X_initial, y_training=y_initial,
)

# the active learning loop
n_queries = 10
for idx in range(n_queries):
    query_idx, query_instance = learner.query(X_pool, n_instances=100)
    learner.teach(X_pool[query_idx], y_pool[query_idx], only_new=True)
    # remove queried instance from pool
    X_pool = np.delete(X_pool, query_idx, axis=0)
    y_pool = np.delete(y_pool, query_idx, axis=0)

# the final accuracy score
print(learner.score(X_test, y_test))