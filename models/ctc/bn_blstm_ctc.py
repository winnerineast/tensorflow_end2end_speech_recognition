#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Batch Normalized bidirectional LSTM-CTC model."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
from models.ctc.base import CTCBase
from recurrent.layers.bn_lstm import BatchNormLSTMCell
from recurrent.initializer import orthogonal_initializer


class BN_BLSTM_CTC(CTCBase):
    """Batch Normalized Bidirectional LSTM-CTC model.
    Args:
        batch_size: int, batch size of mini batch
        input_size: int, the dimensions of input vectors
        num_units: int, the number of units in each layer
        num_layers: int, the number of layers
        num_classes: int, the number of classes of target labels
            (except for a blank label)
        parameter_init: A float value. Range of uniform distribution to
            initialize weight parameters
        clip_grad: A float value. Range of gradient clipping (> 0)
        clip_activation: A float value. Range of activation clipping (> 0)
        num_proj: int, the number of nodes in recurrent projection layer
        weight_decay: A float value. Regularization parameter for weight decay
        bottleneck_dim: int, the dimensions of the bottleneck layer
        is_training: bool, set True when training
        name: string, the name of the CTC model
    """

    def __init__(self,
                 batch_size,
                 input_size,
                 num_units,
                 num_layers,
                 num_classes,
                 parameter_init=0.1,
                 clip_grad=None,
                 clip_activation=None,
                 dropout_ratio_input=1.0,
                 dropout_ratio_hidden=1.0,
                 num_proj=None,
                 weight_decay=0.0,
                 bottleneck_dim=None,
                 is_training=True,
                 name='bn_blstm_ctc'):

        CTCBase.__init__(self, batch_size, input_size, num_units, num_layers,
                         num_classes, parameter_init,
                         clip_grad, clip_activation,
                         dropout_ratio_input, dropout_ratio_hidden,
                         weight_decay, name)

        self.bottleneck_dim = bottleneck_dim
        self.num_proj = None if num_proj == 0 else num_proj
        self._is_training = is_training

    def _build(self, inputs, inputs_seq_len, keep_prob_input,
               keep_prob_hidden):
        """Construct model graph.
        Args:
            inputs: A tensor of `[batch_size, max_time, input_dim]`
            inputs_seq_len:  A tensor of `[batch_size]`
            keep_prob_input:
            keep_prob_hidden:
        Returns:
            logits:
        """
        # Dropout for inputs
        outputs = tf.nn.dropout(inputs,
                                keep_prob_input,
                                name='dropout_input')

        self.is_training = tf.placeholder(tf.bool)

        # Hidden layers
        for i_layer in range(self.num_layers):
            with tf.name_scope('blstm_hidden' + str(i_layer + 1)):

                # initializer = tf.random_uniform_initializer(
                #     minval=-self.parameter_init,
                #     maxval=self.parameter_init)
                initializer = orthogonal_initializer()

                lstm_fw = BatchNormLSTMCell(self.num_units,
                                            use_peepholes=True,
                                            cell_clip=self.clip_activation,
                                            initializer=initializer,
                                            num_proj=self.num_proj,
                                            forget_bias=1.0,
                                            state_is_tuple=True,
                                            is_training=self.is_training)

                lstm_bw = BatchNormLSTMCell(self.num_units,
                                            use_peepholes=True,
                                            cell_clip=self.clip_activation,
                                            initializer=initializer,
                                            num_proj=self.num_proj,
                                            forget_bias=1.0,
                                            state_is_tuple=True,
                                            is_training=self.is_training)
                # num_proj=int(self.num_units / 2),

                # Dropout for outputs of each layer
                lstm_fw = tf.contrib.rnn.DropoutWrapper(
                    lstm_fw,
                    output_keep_prob=keep_prob_hidden)
                lstm_bw = tf.contrib.rnn.DropoutWrapper(
                    lstm_bw,
                    output_keep_prob=keep_prob_hidden)

                # _init_state_fw = lstm_fw.zero_state(self.batch_size,
                #                                     tf.float32)
                # _init_state_bw = lstm_bw.zero_state(self.batch_size,
                #                                     tf.float32)
                # initial_state_fw=_init_state_fw,
                # initial_state_bw=_init_state_bw,

                # Ignore 2nd return (the last state)
                (outputs_fw, outputs_bw), final_state = tf.nn.bidirectional_dynamic_rnn(
                    cell_fw=lstm_fw,
                    cell_bw=lstm_bw,
                    inputs=outputs,
                    sequence_length=inputs_seq_len,
                    dtype=tf.float32,
                    scope='blstm_dynamic' + str(i_layer + 1))

                outputs = tf.concat(axis=2, values=[outputs_fw, outputs_bw])

        # Reshape to apply the same weights over the timesteps
        if self.num_proj is None:
            output_node = self.num_units * 2
        else:
            output_node = self.num_proj * 2
        outputs = tf.reshape(outputs, shape=[-1, output_node])

        # inputs: `[batch_size, max_time, input_size_splice]`
        batch_size = tf.shape(inputs)[0]

        if self.bottleneck_dim is not None and self.bottleneck_dim != 0:
            with tf.name_scope('bottleneck'):
                # Affine
                W_bottleneck = tf.Variable(tf.truncated_normal(
                    shape=[output_node, self.bottleneck_dim],
                    stddev=0.1, name='W_bottleneck'))
                b_bottleneck = tf.Variable(tf.zeros(
                    shape=[self.bottleneck_dim], name='b_bottleneck'))
                outputs = tf.matmul(outputs, W_bottleneck) + b_bottleneck
                output_node = self.bottleneck_dim

        with tf.name_scope('output'):
            # Affine
            W_output = tf.Variable(tf.truncated_normal(
                shape=[output_node, self.num_classes],
                stddev=0.1, name='W_output'))
            b_output = tf.Variable(tf.zeros(
                shape=[self.num_classes], name='b_output'))
            logits_2d = tf.matmul(outputs, W_output) + b_output

            # Reshape back to the original shape
            logits = tf.reshape(
                logits_2d, shape=[batch_size, -1, self.num_classes])

            # Convert to time-major: `[max_time, batch_size, num_classes]'
            logits = tf.transpose(logits, (1, 0, 2))

            return logits
