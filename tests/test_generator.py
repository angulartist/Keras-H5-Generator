from __future__ import absolute_import

import os

import pytest

from h5imagegenerator import HDF5ImageGenerator
from keras.preprocessing.image import ImageDataGenerator
from keras.utils import to_categorical
from keras.models import Sequential, Model
from keras.layers import Dense, Input, SeparableConv2D, Flatten
from sklearn.preprocessing import LabelEncoder
from albumentations import (
    Compose, HorizontalFlip, RandomGamma,
    ToFloat, Resize
)
import numpy as np
import h5py as h5
import cv2
        
def create_generator(
    num_classes=2,
    batch_size=16,
    labels_encoding_mode='smooth',
    smooth_factor=0.1,
    h=227, w=227):
    
    my_augmenter = Compose([
        HorizontalFlip(p=0.5),
        RandomGamma(gamma_limit=(80, 120), p=0.5),
        Resize(h, w, cv2.INTER_AREA),
        # ToFloat(max_value=255)
    ])
    
    gen = HDF5ImageGenerator(
        src='../../storage/datasets/test.h5',
        num_classes=num_classes,
        scaler=True,
        labels_encoding=labels_encoding_mode,
        smooth_factor=smooth_factor,
        batch_size=batch_size,
        augmenter=my_augmenter)

    return gen
    
def create_sequential_model(num_classes=2, shape=(227, 227, 3)):    
    model = Sequential()
    model.add(SeparableConv2D(32,  (5, 5), input_shape=shape, padding='same', activation='relu'))
    model.add(Flatten())
    model.add(Dense(32, activation='relu'))
    model.add(Dense(num_classes, activation='softmax'))
    
    return model

def labels_smoothing(y, factor=0.1):
    y *= (1 - factor)
    y += (factor / y.shape[1])

    return y

def test_labels_encoding():
    classes = ['Cat', 'Dog', 'Panda', 'Bird', 'Zebra']
    y = [np.random.choice(classes) for _ in range(16)]
    le = LabelEncoder()
    scalar_labels = le.fit_transform(y)

    gen = create_generator(num_classes=len(classes))
    binary_matrix = gen.apply_labels_encoding(scalar_labels)
    smooth_binary_matrix = gen.apply_labels_encoding(scalar_labels, 0.1)
    
    assert np.array_equal(
        to_categorical(scalar_labels, num_classes=len(classes)),
        binary_matrix)
    'generated binary matrix should be equal to the output of to_categorical'
    
    assert np.array_equal(
        labels_smoothing(to_categorical(scalar_labels,num_classes=len(classes)), 0.1),
        smooth_binary_matrix)
    'same with labels smoothing'

    
def test_normalization():
    X = np.array([
        [100, 200, 127],
        [75, 225, 127],
        [50, 250, 127],
        [25, 255, 127]
    ])
    test_X = X.astype('float32') / 255.0
        
    gen = create_generator()
    normalized_X = gen.apply_normalization(X)
    
    assert np.array_equal(normalized_X, test_X), 'normalized_X is in the range [0, 1]'
    
def deprecated_test_standardization():
    X = np.array([
        [100, 200, 127],
        [75, 225, 127],
        [50, 250, 127],
        [25, 255, 127]
    ])
    
    gen = create_generator()
    std_X = gen.apply_standardization(X)
    
    X  = X.astype('float32') 
    X -= np.mean(X, keepdims=True)
    X /= (np.std(X, keepdims=True) + 1e-6)
    
    assert np.array_equal(std_X, X), 'std is in the range [-1, 1]'
    
def test_get_next_batch():
    gen = create_generator(batch_size=32)
    
    X, y = gen[np.random.randint(10)]
        
    assert X.shape == (32, 227, 227, 3), 'equals to 32, 227x227x3 images'
    assert y.shape == (32, 2),           'equals to 32 labels (2 classes)'

def test_generator():
    from pytictoc import TicToc
    
    print('Max workers:', os.cpu_count())
    
    train_gen   = create_generator(batch_size=32, h=28, w=28)
    val_gen     = create_generator(batch_size=32, h=28, w=28)
    model       = create_sequential_model(shape=(28, 28, 3))
        
    model.compile(
        loss='categorical_crossentropy',
        metrics=['accuracy'],
        optimizer='rmsprop')
    
    with TicToc():
        model.fit_generator(
            train_gen,
            validation_data=val_gen,
            steps_per_epoch=len(train_gen),
            validation_steps=len(val_gen),
            workers=os.cpu_count(),
            use_multiprocessing=True,
            max_queue_size=os.cpu_count(),
            verbose=1,
            epochs=1,
          )
    
    assert True

if __name__ == '__main__':
    pytest.main([__file__])
