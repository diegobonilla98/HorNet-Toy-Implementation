import torch.nn
import numpy as np
import tqdm
from Model import hornet_small_7x7
from CustomDataLoader import DogCats, Flowers102
from torch.utils.data import DataLoader
from torch.optim import AdamW, lr_scheduler
from torch.autograd import Variable
import matplotlib.pyplot as plt


BATCH_SIZE = 16
LEARNING_RATE = 1e-3
USE_CUDA = torch.cuda.is_available()
N_EPOCHS = 100
IMAGE_SIZE = (224, 224)

model = hornet_small_7x7(in_chans=3, num_classes=102)
print(model)

data_loader = DataLoader(Flowers102(IMAGE_SIZE, augment=False), batch_size=BATCH_SIZE, shuffle=True)

optimizer = AdamW(model.parameters(), lr=LEARNING_RATE)
lambda1 = lambda epoch: 0.65 ** epoch
scheduler = lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda1)
loss_class = torch.nn.NLLLoss()

if USE_CUDA:
    model = model.cuda()
    loss_class = loss_class.cuda()

for p in model.parameters():
    p.requires_grad = True

best_loss = np.inf
epochs_without_improvement = 0

for epoch in range(N_EPOCHS + 1):
    data_iter = iter(data_loader)
    i = 0
    epoch_losses = []
    with tqdm.tqdm(total=len(data_loader)) as pbar:
        while i < len(data_loader):
            sample = next(data_iter)
            s_image, s_label = sample['image'], sample['class']
            s_label = s_label.long()

            optimizer.zero_grad()
            if USE_CUDA:
                s_image = s_image.cuda()
                s_label = s_label.cuda()

            s_image_v = Variable(s_image)
            s_label_v = Variable(s_label)

            s_class_output = model(s_image_v)
            err = loss_class(s_class_output, s_label_v)

            err.backward()
            optimizer.step()

            i += 1

            epoch_losses.append(err.cpu().data.numpy())

            pbar.set_description(f"Iter: {i}/{len(data_loader)}, [Loss: {np.mean(epoch_losses)}]")
            pbar.update()

    epoch_loss = np.mean(epoch_losses)
    if best_loss - epoch_loss > 0.00005:
        epochs_without_improvement = 0
        best_loss = epoch_loss
        torch.save(model, f'./checkpoints/best_model.pth')
    else:
        epochs_without_improvement += 1
        scheduler.step()
        if epochs_without_improvement == 5:
            break
    print(f'[Epoch: {epoch}/{N_EPOCHS}, [Loss: {epoch_loss}]')
