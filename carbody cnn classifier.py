# -*- coding: utf-8 -*-
"""notebook33435a43aa.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1VJVBm9EVEkT-_AxxkQMounBWEon5yO4Q
"""

import numpy as np 
import pandas as pd
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms,models
from torch.utils.data.sampler import SubsetRandomSampler
from torchvision.utils import make_grid
import cv2
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import shutil
import random

torch.cuda.empty_cache()

class_label = ('Cab','Convertible','Coupe','Hatchback','Minivan','Other','SUV','Sedan','Van','Wagon')

ls /kaggle/input/stanford-car-body-type-data/stanford_cars_type

dataset = datasets.ImageFolder('/kaggle/input/stanford-car-body-type-data/stanford_cars_type', transform = transforms.Compose([transforms.Resize((299,299)),
                                                                                                                               transforms.ToTensor()]))

batch_size = 32

train_transforms = transforms.Compose([transforms.ToPILImage(),
                                       transforms.RandomResizedCrop(299),
                                       transforms.RandomHorizontalFlip(),
                                       transforms.ToTensor(),
                                       transforms.ColorJitter(),
                                       transforms.Normalize([0.4687, 0.4582, 0.4534],
                                                            [0.2885, 0.2878, 0.2962]),
                                       transforms.RandomErasing()])

test_transforms = transforms.Compose([transforms.ToPILImage(),
                                      transforms.ToTensor(),
                                      transforms.Normalize([0.4687, 0.4582, 0.4534],
                                                           [0.2885, 0.2878, 0.2962])])

class Dataset(torch.utils.data.Dataset):
  'Characterizes a dataset for PyTorch'
  def __init__(self, samples, transform):
        'Initialization'
        self.samples = samples
        self.transform = transform

  def __len__(self):
        'Denotes the total number of samples'
        return len(self.samples)

  def __getitem__(self, index):
        'Generates one sample of data'
        x = self.samples[index][0]
        if self.transform:
            x = self.transform(x)
        
        y = self.samples[index][1]

        return x, y

traindata = Dataset(dataset,transform = train_transforms)

testdata = Dataset(dataset, transform = test_transforms)

train_size = 0.8
num_train = len(dataset)
indices = list(range(num_train))
indices = random.sample(indices, num_train)
split = int(np.floor(train_size * num_train))

train_idx, test_idx = indices[:split], indices[split:]

train_set = torch.utils.data.Subset(traindata, indices=train_idx)
test_set = torch.utils.data.Subset(testdata, indices=test_idx)

trainloader = torch.utils.data.DataLoader(train_set,batch_size=batch_size,shuffle=True)
testloader = torch.utils.data.DataLoader(test_set, batch_size=batch_size)

input, classes = next(iter(testloader))

car = 2
plt.imshow(input[car].permute(1,2,0)) , class_label[classes[car].item()]


class GoogLeNet(nn.Module):
  def __init__(self, in_channels=3, num_classes=10):
    super(GoogLeNet, self).__init__()

    self.conv1 = conv_block(in_channels=in_channels, out_channels=64, kernel_size=(7,7), stride=(2,2), padding=(3,3))

    self.maxpool1 = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
    self.conv2 = conv_block(64, 192, kernel_size=3, stride=1, padding=1)
    self.maxpool2 = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

    # in_channels, out_1x1, red_3x3, out_3x3, red_5x5, out_5x5, out_1x1pool

    self.inception3a = Inception_block(192, 64, 96, 128, 16, 32, 32)
    self.inception3b = Inception_block(256, 128, 128, 192, 32, 96, 64)
    self.maxpool3 = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

    self.inception4a = Inception_block(480, 192, 96, 208, 16, 48, 64)
    self.inception4b = Inception_block(512, 160, 112, 224, 24, 64, 64)
    self.inception4c = Inception_block(512, 128, 128, 256, 24, 64, 64)
    self.inception4d = Inception_block(512, 112, 144, 288, 32, 64, 64)
    self.inception4e = Inception_block(528, 256, 160, 320, 32, 128, 128)
    self.maxpool4 = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

    self.inception5a = Inception_block(832, 256, 160, 320, 32, 128, 128)
    self.inception5b = Inception_block(832, 384, 192, 384, 48, 128, 128)

    self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
    self.dropout = nn.Dropout(p=0.4)
    self.fc1 = nn.Linear(1024, 10)

  def forward(self ,x):
    x = self.conv1(x)
    x = self.maxpool1(x)
    x = self.conv2(x)
    x = self.maxpool2(x)

    x = self.inception3a(x)
    x = self.inception3b(x)
    x = self.maxpool3(x)

    x = self.inception4a(x)
    x = self.inception4b(x) 
    x = self.inception4c(x)
    x = self.inception4d(x)
    x = self.inception4e(x)
    x = self.maxpool4(x)

    x = self.inception5a(x)
    x = self.inception5b(x)

    x = self.avgpool(x)
    x = self.dropout(x)
    x = x.view(x.size()[0], -1)
    x = self.fc1(x)
    return x

class Inception_block(nn.Module):
  def __init__(self, in_channels, out_1x1, red_3x3, out_3x3, red_5x5, out_5x5, out_1x1pool):
    super(Inception_block, self).__init__()
    self.branch1 = conv_block(in_channels, out_1x1, kernel_size=1)
    self.branch2 = nn.Sequential(
        conv_block(in_channels, red_3x3, kernel_size=1),
        conv_block(red_3x3, out_3x3, kernel_size=3, padding=1)
        )
    self.branch3 = nn.Sequential(
        conv_block(in_channels, red_5x5, kernel_size=1),
        conv_block(red_5x5, out_5x5, kernel_size=5, padding=2)
        )
    self.branch4 = nn.Sequential(
        nn.MaxPool2d(kernel_size=3, stride=1, padding=1),
        conv_block(in_channels, out_1x1pool, kernel_size=1)
        )

  def forward(self, x):
    return torch.cat([self.branch1(x), self.branch2(x), self.branch3(x), self.branch4(x)], 1)


class conv_block(nn.Module):
    def __init__(self, in_channels, out_channels, **kwargs):
      super(conv_block, self).__init__()
      self.relu = nn.ReLU()
      self.conv = nn.Conv2d(in_channels, out_channels, **kwargs)
      self.batchnorm = nn.BatchNorm2d(out_channels)

    def forward(self, x):
      return self.relu(self.batchnorm(self.conv(x)))

device = 'cuda' if torch.cuda.is_available() else 'cpu'

model = GoogLeNet().to(device)

optimizer = optim.SGD(model.parameters(), lr=0.001)
criterion = nn.CrossEntropyLoss()

def training_loop(epochs):
    correct_train = 0
    correct_test = 0
    #correct_top_5 = 0
    total_train = 0
    total_test = 0
    training_loss = 0
    eval_loss = 0
    epoch = 0
    for epoch in range(epochs):
        model.train()
        for batch_idx, (inputs, targets) in enumerate(trainloader):
              # Move inputs and labels to chosen device
              images_train, labels_train = inputs.to(device), targets.to(device)
              # Clear gradients from previous phase
              optimizer.zero_grad()
              # Forward pass
              pred_train = model(images_train)
              # Calculating cost function -> inception version 3 has two outputs, aux_logits = False
              train_loss = criterion(pred_train, labels_train)
              # Propagating loss through network
              train_loss.backward()
              # Performing weights update
              optimizer.step()
              # Extract index of highest scored prediciton
              _, predicted_train = torch.max(pred_train, 1)
              # Iterate through all dataset and add all batches every epoch
              total_train += float(labels_train.size(0))
              # Check if predicitons and labels are same. They are in batches, that's why we use sum function. Finally .item() is useful to extract number from tensor.
              correct_train += (predicted_train == labels_train).sum().item()
              # Calculating training loss for further evaluation
              #training_loss += train_loss.item()
        # Calculating accuracy/loss for one epoch
        accuracy = 100 * float(correct_train) / float(total_train)
        epoch +=1
        #tr_loss = training_loss / total_train
        print("Train accuracy = {}% , Epoch = {}".format(accuracy,epoch))

        #################### EVALUATION PHASE ####################
        model.eval()
        with torch.no_grad():
            for data_test in testloader:
              # Move inputs and labels to chosen device
              images_test, labels_test  = data_test[0].to(device), data_test[1].to(device)
              # Forward pass
              pred_test = model(images_test)
              # Calculating cost function
              test_loss = criterion(pred_test, labels_test)

              ########## Top 1 accuracy calculation ##########
              
              # Extract index of highest scored prediciton
              _,predicted_test = torch.max(pred_test.data,1)
              # Iterate through all dataset and add all batches every epoch
              total_test += float(labels_test.size(0))
              # Check if predicitons and labels are same. They are in batches, that's why we use sum function. Finally .item() is useful to extract number from tensor.
              correct_test += (predicted_test == labels_test).sum().item()
              # Calculating test loss for further evaluation
              #eval_loss += test_loss.item()
              # Calculating test accuracy/loss for one epoch
              test_accuracy = 100 * float(correct_test) / float(total_test)
              #ts_loss = eval_loss / total_test
              
              ########## Top 5 accuracy calculation ##########

              # Extract indexes of 5 highest scored predicitons
              #_, pred_test_top_5 = pred_test.topk(2, dim = 1, largest = True, sorted = True)
              # Transpose array for expand function
              #pred_test_top_5 = pred_test_top_5.t()
              # Check if predicitons and labels are same. Labels are predicted for example if 5 highest scores indexes are [0,2,5,6,1], 
              # we comparing this with true label e.g [1], so we have to expand it. Finally we are comparing if [0,2,5,6,1] == [1,1,1,1,1] -> [False,False,False,False,True]
              #top_5 = pred_test_top_5.eq(labels_test.view(1, -1).expand_as(pred_test_top_5))
              # Sum list to get 0 or 1
              #correct_top_5 += top_5[:2].reshape(-1).float().sum().item()
              # Calculating top 5 accuracy for one epoch
              #top_5_acc = 100 * correct_top_5 / total_test
              

            print("Test_accuracy: top 1 = {}%".format(test_accuracy))
            #print("Test_accuracy: top 5 = {:.3f}%".format(top_5_acc))

optimizer_ft = optim.Adam(model.parameters(), lr=0.0001)
criterion = nn.CrossEntropyLoss()
training_loop(40)

torch.save({
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict()
            }, '/kaggle/working/model.pth')