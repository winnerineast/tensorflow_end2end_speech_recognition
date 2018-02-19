#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""A collection of bridges between encoder and decoder. A bridge defines
how encoder information are passed to the decoder.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc
from pydoc import locate

import six
import numpy as np

import tensorflow as tf
from tensorflow.python.util import nest


def _total_tensor_depth(tensor):
    """Returns the size of a tensor without the first (batch) dimension"""
    return np.prod(tensor.get_shape().as_list()[1:])


@six.add_metaclass(abc.ABCMeta)
class Bridge(object):
    """An abstract bridge class. A bridge defines how state is passed
    between encoder and decoder.
    All logic is contained in the `_create` method, which returns an
    initial state for the decoder.
    Args:
        encoder_outputs (namedtuple): A namedtuple that corresponds to the the
            encoder outputs.
            `(outputs, final_state, seq_len)`
        decoder_state_size: An integer or tuple of integers defining the
            state size of the decoder.
    """

    def __init__(self, encoder_outputs, decoder_state_size):
        self.encoder_outputs = encoder_outputs
        self.decoder_state_size = decoder_state_size
        self.batch_size = tf.shape(
            nest.flatten(self.encoder_outputs.final_state)[0])[0]

    def __call__(self):
        """Runs the bridge function.
        Returns:
            An initial decoder_state tensor or tuple of tensors.
        """
        return self._create()

    @abc.abstractmethod
    def _create(self):
        """ Implements the logic for this bridge.
        This function should be implemented by child classes.
        Returns:
            A tuple initial_decoder_state tensor or tuple of tensors.
        """
        raise NotImplementedError("Must be implemented by child class")


class ZeroBridge(Bridge):
    """A bridge that does not pass any information between encoder and decoder
    and sets the initial decoder state to 0. The input function is not
    modified.
    """

    @staticmethod
    def default_params():
        return {}

    def _create(self):
        zero_state = nest.map_structure(
            lambda x: tf.zeros([self.batch_size, x], dtype=tf.float32),
            self.decoder_state_size)
        return zero_state


class PassThroughBridge(Bridge):
    """Passes the encoder state through to the decoder as-is. This bridge
    can only be used if encoder and decoder have the exact same state size,
    i.e. use the same RNN cell.
    """

    @staticmethod
    def default_params():
        return {}

    def _create(self):
        nest.assert_same_structure(self.encoder_outputs.final_state,
                                   self.decoder_state_size)
        return self.encoder_outputs.final_state


class InitialStateBridge(Bridge):
    """A bridge that creates an initial decoder state based on the output
    of the encoder. This state is created by passing the encoder outputs
    through an additional layer to match them to the decoder state size.
    The input function remains unmodified.
    Args:
        encoder_outputs (namedtuple): A namedtuple that corresponds to the
            encoder outputs.
            `(outputs, final_state, seq_len)`
        decoder_state_size: An integer or tuple of integers defining the
            state size of the decoder.
    """

    def __init__(self, encoder_outputs, decoder_state_size, parameter_init):
        super(InitialStateBridge, self).__init__(encoder_outputs,
                                                 decoder_state_size)

        if not hasattr(encoder_outputs, "final_state"):
            raise ValueError("Invalid bridge_input not in encoder outputs.")

        self._bridge_input = getattr(encoder_outputs, "final_state")
        self._activation_fn = locate("tensorflow.identity")
        self.parameter_init = parameter_init

    @staticmethod
    def default_params():
        return {
            "bridge_input": "final_state",
            "activation_fn": "tensorflow.identity",
        }

    def _create(self):
        # Concat bridge inputs on the depth dimensions
        bridge_input = nest.map_structure(
            lambda x: tf.reshape(x, [self.batch_size, _total_tensor_depth(x)]),
            self._bridge_input)
        bridge_input_flat = nest.flatten([bridge_input])
        bridge_input_concat = tf.concat(bridge_input_flat, axis=1)

        state_size_splits = nest.flatten(self.decoder_state_size)
        total_decoder_state_size = sum(state_size_splits)

        # Pass bridge inputs through a fully connected layer layer
        initial_state_flat = tf.contrib.layers.fully_connected(
            bridge_input_concat,
            num_outputs=total_decoder_state_size,
            activation_fn=self._activation_fn,
            weights_initializer=tf.truncated_normal_initializer(
                stddev=self.parameter_init),
            biases_initializer=tf.zeros_initializer(),
            scope=None)

        # Shape back into required state size
        initial_state = tf.split(initial_state_flat, state_size_splits, axis=1)
        return nest.pack_sequence_as(self.decoder_state_size, initial_state)
