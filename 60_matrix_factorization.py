import statistics
import glob
import math
import pickle
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.init as weight_init
from torch.autograd import Variable
import torch.nn.functional as F


class MF(nn.Module):
    def __init__(self, input_items, input_users):
        super(MF, self).__init__()
        print('item size', input_items)

        self.l_b1 = nn.Embedding(num_embeddings=input_items, embedding_dim=768)
        self.l_b2 = nn.Linear(
            in_features=768, out_features=512, bias=True)

        self.l_a1 = nn.Embedding(num_embeddings=input_users, embedding_dim=768)
        self.l_a2 = nn.Linear(
            in_features=768, out_features=512, bias=True)

        self.l_l1 = nn.Linear(
            in_features=512, out_features=1, bias=True)

    def encode_item(self, x):
        x = self.l_b1(x)
        x = F.relu(self.l_b2(x))
        return x

    def encode_user(self, x):
        x = self.l_a1(x)
        x = F.relu(self.l_a2(x))
        return x


    def forward(self, inputs):
        item_vec, user_vec = inputs
        item_vec = self.encode_item(item_vec)
        batch_size = list(item_vec.size())[0]

        user_vec = self.encode_user(user_vec)
        # doted = torch.bmm(user_vec.view(batch_size, 1, 100),
        #                  item_vec.view(batch_size, 100, 1))
        return F.relu(self.l_l1(user_vec * item_vec))


def myLoss(output, target):
    loss = torch.sqrt(torch.mean((output-target)**2))
    return loss


def generate():
    train_triples = pickle.load(open('works/dataset/train_triples.pkl', 'rb'))

    BATCH = 32
    for i in range(0, len(train_triples), BATCH):
        array = np.array(train_triples[i:i+BATCH])
        uindex = array[:, 0]
        mindex = array[:, 1]
        scores = array[:, 2]
        yield uindex, mindex, scores


test_triples = pickle.load(open('works/dataset/test_triples.pkl', 'rb'))
def validate(model, device):
    array = np.array(test_triples)
    model.to(device)
    losses = []
    for i in range(0, array.shape[0], 100):
        uindex = array[i:i+100, 0]
        mindex = array[i:i+100, 1]
        scores = array[i:i+100, 2]
        inputs = [
            Variable(torch.from_numpy(mindex)).long().to(device),
            Variable(torch.from_numpy(uindex)).long().to(device),
        ]
        scores = Variable(torch.from_numpy(
            scores)).float().to(device)
        loss = myLoss(scores, model.to(device)(inputs))
        losses.append(float(loss.data.cpu().numpy()))
        del inputs
    print('rmse', statistics.mean(losses))
    model.to(device)


if __name__ == '__main__':

    device = 'cuda'
    movie_index = json.load(open('./works/defs/smovie_index.json'))
    user_index = json.load(open('./works/defs/user_index.json'))
    print('user size', len(user_index), 'item size', len(movie_index))
    model = MF(len(movie_index), len(user_index)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)

    for index, (uindex, mindex, scores) in enumerate(generate()):
        uindex_t = Variable(torch.from_numpy(
            uindex)).long().to(device)
        mindex_t = Variable(torch.from_numpy(
            mindex)).long().to(device)
        predict = model([mindex_t, uindex_t])

        scores = Variable(torch.from_numpy(
            scores)).float().to(device)

        loss = nn.MSELoss()(predict, scores)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if index % 500 == 0:
            validate(model, device)

        # torch.save(model.state_dict(), f'conv_autoencoder_{epoch:04d}.pth')
