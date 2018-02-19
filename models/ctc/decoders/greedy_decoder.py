#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Greedy (best pass) decoder."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
from itertools import groupby


class GreedyDecoder(object):

    def __init__(self, blank_index):
        self.blank = blank_index

    def __call__(self, probs, seq_len):
        """
        Args:
            probs (np.ndarray): A tensor of size `[B, T, num_classes]`
            seq_len (np.ndarray): A tensor of size `[B]`
        Returns:
            results (np.ndarray): Best path hypothesis, A tensor of size `[B, max_len]`
        """
        # Convert to log scale
        log_probs = np.log(probs)

        batch_size = log_probs.shape[0]
        results = [] * batch_size

        # Pickup argmax class
        for i_batch in range(batch_size):
            indices = []
            time = seq_len[i_batch]
            for t in range(time):
                arg_max = np.argmax(log_probs[i_batch][t], axis=0)
                indices.append(arg_max)

            # Step 1. Collapse repeated labels
            collapsed_indices = [x[0] for x in groupby(indices)]

            # Step 2. Remove all blank labels
            best_hyp = [x for x in filter(
                lambda x: x != self.blank, collapsed_indices)]

            results.append(best_hyp)

        return np.array(results)
