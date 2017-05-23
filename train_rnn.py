#  Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Example of Estimator for DNN-based text classification with DBpedia data."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys

import numpy as np
import pandas
from sklearn import metrics
import tensorflow as tf
from tensorflow.contrib.layers.python.layers import encoders

learn = tf.contrib.learn
from sklearn.preprocessing import LabelBinarizer

import data_utils

FLAGS = None

MAX_DOCUMENT_LENGTH = 10000
EMBEDDING_SIZE = 500
n_words = 100000


def bag_of_words_model(features, target):
    """A bag-of-words model. Note it disregards the word order in the text."""
    target = tf.one_hot(target, 15, 1, 0)
    features = encoders.bow_encoder(
        features, vocab_size=n_words, embed_dim=EMBEDDING_SIZE)
    logits = tf.contrib.layers.fully_connected(features, 15, activation_fn=None)
    loss = tf.contrib.losses.softmax_cross_entropy(logits, target)
    train_op = tf.contrib.layers.optimize_loss(
        loss,
        tf.contrib.framework.get_global_step(),
        optimizer='Adam',
        learning_rate=0.01)
    return ({
                'class': tf.argmax(logits, 1),
                'prob': tf.nn.softmax(logits)
            }, loss, train_op)


def rnn_model(features, target):
    """RNN model to predict from sequence of words to a class."""
    # Convert indexes of words into embeddings.
    # This creates embeddings matrix of [n_words, EMBEDDING_SIZE] and then
    # maps word indexes of the sequence into [batch_size, sequence_length,
    # EMBEDDING_SIZE].
    word_vectors = tf.contrib.layers.embed_sequence(
        features, vocab_size=n_words, embed_dim=EMBEDDING_SIZE, scope='words')

    # Split into list of embedding per word, while removing doc length dim.
    # word_list results to be a list of tensors [batch_size, EMBEDDING_SIZE].
    word_list = tf.unstack(word_vectors, axis=1)

    # Create a Gated Recurrent Unit cell with hidden size of EMBEDDING_SIZE.
    cell = tf.contrib.rnn.GRUCell(EMBEDDING_SIZE)

    # Create an unrolled Recurrent Neural Networks to length of
    # MAX_DOCUMENT_LENGTH and passes word_list as inputs for each unit.
    _, encoding = tf.contrib.rnn.static_rnn(cell, word_list, dtype=tf.float32)

    # Given encoding of RNN, take encoding of last step (e.g hidden size of the
    # neural network of last step) and pass it as features for logistic
    # regression over output classes.
    # target = tf.one_hot(target, 15, 1, 0)
    logits = tf.contrib.layers.fully_connected(encoding, 2794, activation_fn=None)
    loss = tf.losses.softmax_cross_entropy(logits, target)
    tf.losses.softmax_cross_entropy(onehot_labels=tar)
    # Create a training op.
    train_op = tf.contrib.layers.optimize_loss(
        loss,
        tf.contrib.framework.get_global_step(),
        optimizer='Adam',
        learning_rate=0.01)

    return ({
                'class': tf.argmax(logits, 1),
                'prob': tf.nn.softmax(logits)
            }, loss, train_op)


def main(unused_argv):
    global n_words
    # Prepare training and testing data
    data, label = data_utils.read_raw_data(FLAGS.data_dir + FLAGS.data_file, FLAGS.data_dir + FLAGS.label_file)
    # Process vocabulary
    vocab_processor = learn.preprocessing.VocabularyProcessor(MAX_DOCUMENT_LENGTH)

    x = np.array(list(vocab_processor.fit_transform(data)))
    del data
    # Process label to one hot vector
    lb = LabelBinarizer()
    y = lb.fit_transform(label)
    del label
    # np.random.seed(10)
    # shuffle_indices = np.random.permutation(np.arange(len(y)))
    # x_shuffled = tf.random_shuffle(x, seed=10)
    # y_shuffled = tf.random_shuffle(y, seed=10)
    # x_shuffled = x[shuffle_indices]
    # y_shuffled = y[shuffle_indices]
    x_shuffled = x
    y_shuffled = y
    dev_sample_index = -1 * int(FLAGS.test_sample_percentage * float(len(y)))
    x_train, x_test = x_shuffled[:dev_sample_index], x_shuffled[dev_sample_index:]
    y_train, y_test = y_shuffled[:dev_sample_index], y_shuffled[dev_sample_index:]
    # pdb.set_trace()

    # Build model
    # Switch between rnn_model and bag_of_words_model to test different models.
    model_fn = rnn_model
    if FLAGS.bow_model:
        model_fn = bag_of_words_model

    classifier = learn.SKCompat(learn.Estimator(model_fn=model_fn))

    # Train and predict
    classifier.fit(x_train, y_train, steps=100)
    y_predicted = [
        p['class'] for p in classifier.predict(x_test, as_iterable=True)]
    score = metrics.accuracy_score(y_test, y_predicted)
    print('Accuracy: {0:f}'.format(score))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--test_with_fake_data',
        default=False,
        help='Test the example code with fake data.',
        action='store_true'
    )
    parser.add_argument(
        '--bow_model',
        default=False,
        help='Run with BOW model instead of RNN.',
        action='store_true'
    )
    parser.add_argument(
        '--data_dir',
        default="../../data/data_by_ocean/eclipse/",
        help='data direction',
        action='store_true'
    )
    parser.add_argument(
        '--data_file',
        default="textForLDA_final.csv",
        help='data path',
        action='store_true'
    )
    parser.add_argument(
        '--label_file',
        default="fixer.csv",
        help='label path',
        action='store_true'
    )
    parser.add_argument(
        '--test_sample_percentage',
        default=.2,
        help='Percentage of the training data to use for test',
        action='store_true'
    )
    parser.add_argument(
        '--vocabulary_size',
        default=100000,
        help='vocabulary size',
        action='store_true'
    )

    FLAGS, unparsed = parser.parse_known_args()
    tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)
