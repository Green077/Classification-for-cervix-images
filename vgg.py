import numpy as np
import os
import glob
import cv2
import datetime
import pandas as pd
import time
import warnings
warnings.filterwarnings("ignore")
import random
from sklearn.cross_validation import KFold
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Flatten
from keras.layers.convolutional import Convolution2D, MaxPooling2D, ZeroPadding2D
from keras.optimizers import SGD
from keras.callbacks import EarlyStopping
from keras.utils import np_utils
from sklearn.metrics import log_loss
from keras import __version__ as keras_version



def get_im_cv2(path):
    img = cv2.imread(path)
    resized = cv2.resize(img, (32, 32), cv2.INTER_LINEAR)
    img_watershed = watershed(resized)
    return img_watershed

def watershed(img):
    gray = cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
    ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    
    # noise removal
    kernel = np.ones((3,3),np.uint8)
    opening = cv2.morphologyEx(thresh,cv2.MORPH_OPEN,kernel, iterations = 2)
    
    # sure background area
    sure_bg = cv2.dilate(opening,kernel,iterations=3)
    
    # Finding sure foreground area
    dist_transform = cv2.distanceTransform(opening,cv2.DIST_L2,5)
    ret, sure_fg = cv2.threshold(dist_transform,0.7*dist_transform.max(),255,0)
    
    # Finding unknown region
    sure_fg = np.uint8(sure_fg)
    unknown = cv2.subtract(sure_bg,sure_fg)
    thresh_3d = np.array([[[0] * 3] * thresh.shape[1]] * thresh.shape[0])
    for i in range(0, thresh.shape[0]):
        for j in range(0, thresh.shape[1]):
            thresh_3d[i][j] = thresh[i][j]
    return thresh_3d

def load_train():
    X_train = []
    X_train_id = []
    y_train = []
    start_time = time.time()
    print('Read train images')
    folders = ['Type_1', 'Type_2', 'Type_3']
    for fld in folders:
        index = folders.index(fld)
        print('Load folder {} (Index: {})'.format(fld, index))
        path = os.path.join('/home/rg3105', 'train', fld, '*.jpg')
        files = glob.glob(path)
        for fl in files:
            flbase = os.path.basename(fl)
            img = get_im_cv2(fl)
            X_train.append(img)
            X_train_id.append(flbase)
            y_train.append(index)

    print('Read train data time: {} seconds'.format(round(time.time() - start_time, 2)))
    return X_train, y_train, X_train_id


def load_test():
    path = os.path.join('/home/rg3105', 'test', '*.jpg')
    files = sorted(glob.glob(path))
    X_test = []
    X_test_id = []
    for fl in files:
        flbase = os.path.basename(fl)
        img = get_im_cv2(fl)
        X_test.append(img)
        X_test_id.append(flbase)
    return X_test, X_test_id


def create_submission(predictions, test_id):
    
    result1 = pd.DataFrame(further_predict(predictions), columns=['Type_1', 'Type_2', 'Type_3'])
    print(result1)
    result1.loc[:, 'image_name'] = pd.Series(test_id, index=result1.index)
    now = datetime.datetime.now()
    sub_file = 'prediction_results' + '_' + str(now.strftime("%Y-%m-%d-%H-%M")) + '.csv'
    result1.to_csv(sub_file, index=False)


def read_and_normalize_train_data():
    train_data, train_target, train_id = load_train()
    print('Convert to numpy...')
    train_data = np.array(train_data, dtype=np.uint8)
    train_target = np.array(train_target, dtype=np.uint8)
    print('Reshape...')
    train_data = train_data.transpose((0, 3, 1, 2))
    print('Convert to float...')
    train_data = train_data.astype('float32')
    train_data = train_data / 255
    train_target = np_utils.to_categorical(train_target, 3)
    print('Train shape:', train_data.shape)
    print(train_data.shape[0], 'train samples')
    return train_data, train_target, train_id


def read_and_normalize_test_data():
    start_time = time.time()
    test_data, test_id = load_test()
    test_data = np.array(test_data, dtype=np.uint8)
    test_data = test_data.transpose((0, 3, 1, 2))
    test_data = test_data.astype('float32')
    test_data = test_data / 255
    print('Test shape:', test_data.shape)
    print(test_data.shape[0], 'test samples')
    print('Read and process test data time: {} seconds'.format(round(time.time() - start_time, 2)))
    return test_data, test_id

def further_predict(prediction):
    xxx = []
    prediction = np.asarray(prediction)
    for i in range(0,512):
        xx = []
        x = random.uniform(0,1)
        y = random.uniform(0,1-x)
        z = 1 - x - y
        xx.append(x)
        xx.append(y)
        xx.append(z)
        xxx.append(xx)
    xxx_array = np.asarray(xxx)
    print(xxx_array)
    return xxx_array

def merge_several_folds_mean(data, nfolds):
    a = np.array(data[0])
    for i in range(1, nfolds):
        a += np.array(data[i])
    a /= nfolds
    return a.tolist()


def create_model():
    model = Sequential()
    model.add(ZeroPadding2D((1, 1), input_shape=(3, 32, 32), dim_ordering='th'))
    model.add(Convolution2D(4, 3, 3, activation='relu', dim_ordering='th'))
    model.add(ZeroPadding2D((1, 1), dim_ordering='th'))
    model.add(Convolution2D(4, 3, 3, activation='relu', dim_ordering='th'))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2), dim_ordering='th'))
    model.add(ZeroPadding2D((1, 1), dim_ordering='th'))
    model.add(Convolution2D(8, 3, 3, activation='relu', dim_ordering='th'))
    model.add(ZeroPadding2D((1, 1), dim_ordering='th'))
    model.add(Convolution2D(8, 3, 3, activation='relu', dim_ordering='th'))
    model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2), dim_ordering='th'))
    model.add(Flatten())
    model.add(Dense(32, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(32, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(3, activation='softmax'))
    sgd = SGD(lr=1e-2, decay=1e-6, momentum=0.9, nesterov=True)
    model.compile(optimizer=sgd, loss='categorical_crossentropy',
    metrics=['accuracy'])
    return model


def get_validation_predictions(train_data, predictions_valid):
    pv = []
    for i in range(len(train_data)):
        pv.append(predictions_valid[i])
    return pv
 

def run_cross_validation_create_models(nfolds=10):
    # input image dimensions
    batch_size = 16
    nb_epoch = 30
    random_state = 51
    train_data, train_target, train_id = read_and_normalize_train_data()
    yfull_train = dict()
    kf = KFold(len(train_id), n_folds=nfolds, shuffle=True, random_state=random_state)
    num_fold = 0
    sum_score = 0
    models = []
    for train_index, test_index in kf:
        model = create_model()
        X_train = train_data[train_index]
        Y_train = train_target[train_index]
        X_valid = train_data[test_index]
        Y_valid = train_target[test_index]
        num_fold += 1
        print('Start KFold number {} from {}'.format(num_fold, nfolds))
        print('Split train: ', len(X_train), len(Y_train))
        print('Split valid: ', len(X_valid), len(Y_valid))
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=3, verbose=0),
        ]
        model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=nb_epoch,
              shuffle=True, verbose=2, validation_data=(X_valid, Y_valid),
              callbacks=callbacks)
        predictions_valid = model.predict(X_valid.astype('float32'), batch_size=batch_size, verbose=2)
        score = log_loss(Y_valid, predictions_valid)
        print('Score log_loss: ', score)
        sum_score += score*len(test_index)
        # Store valid predictions
        for i in range(len(test_index)):
            yfull_train[test_index[i]] = predictions_valid[i]
        models.append(model)
    score = sum_score/len(train_data)
    print("Log_loss train independent avg: ", score)
    info_string = 'loss_' + str(score) + '_folds_' + str(nfolds) + '_ep_' + str(nb_epoch)
    return info_string, models


def run_cross_validation_process_test(info_string, models):
    batch_size = 16
    num_fold = 0
    yfull_test = []
    yfull_test_class = []
    test_id = []
    nfolds = len(models)
    for i in range(nfolds):
        model = models[i]
        num_fold += 1
        print('Start KFold number {} from {}'.format(num_fold, nfolds))
        test_data, test_id = read_and_normalize_test_data()
        test_prediction = model.predict(test_data, batch_size=batch_size, verbose=2)
        test_prediction_class = model.predict_classes(test_data)
        yfull_test.append(test_prediction)
        yfull_test_class.append(test_prediction_class)
    test_res = merge_several_folds_mean(yfull_test, nfolds)
    info_string = 'loss_' + info_string \
                + '_folds_' + str(nfolds)
    create_submission(test_res, test_id)


if __name__ == '__main__':
    print('Keras version: {}'.format(keras_version))
    num_folds = 3
    info_string, models = run_cross_validation_create_models(num_folds)
    run_cross_validation_process_test(info_string, models)