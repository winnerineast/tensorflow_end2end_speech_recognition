#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Define evaluation method for the Attention-based model (CSJ corpus)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
from tqdm import tqdm

from utils.io.labels.character import Idx2char
from utils.evaluation.edit_distance import compute_cer


def do_eval_cer(session, decode_ops, model, dataset, label_type,
                train_data_size,
                is_test=False, eval_batch_size=None, progressbar=False):
    """Evaluate trained model by Character Error Rate.
    Args:
        session: session of training model
        decode_ops (list): operations for decoding
        model: the model to evaluate
        dataset: An instance of a `Dataset` class
        label_type (string): kanji or kanji or kanji_divide or kana_divide
        train_data_size (string): train_subset or train_fullset
        is_test (bool, optional): set to True when evaluating by the test set
        eval_batch_size (int, optional): the batch size when evaluating the model
        progressbar (bool, optional): if True, visualize the progressbar
    Return:
        cer_mean (float): An average of CER
    """
    assert isinstance(decode_ops, list), "decode_ops must be a list."

    batch_size_original = dataset.batch_size

    # Reset data counter
    dataset.reset()

    # Set batch size in the evaluation
    if eval_batch_size is not None:
        dataset.batch_size = eval_batch_size

    if 'kanji' in label_type:
        map_file_path = '../metrics/mapping_files/' + \
            label_type + '_' + train_data_size + '.txt'
    elif 'kana' in label_type:
        map_file_path = '../metrics/mapping_files/' + label_type + '.txt'
    else:
        raise TypeError

    idx2char = Idx2char(map_file_path=map_file_path)

    cer_mean = 0
    if progressbar:
        pbar = tqdm(total=len(dataset))
    for data, is_new_epoch in dataset:

        # Create feed dictionary for next mini batch
        inputs, labels_true, inputs_seq_len, labels_seq_len,  _ = data

        feed_dict = {}
        for i_device in range(len(decode_ops)):
            feed_dict[model.inputs_pl_list[i_device]] = inputs[i_device]
            feed_dict[model.inputs_seq_len_pl_list[i_device]
                      ] = inputs_seq_len[i_device]
            feed_dict[model.keep_prob_encoder_pl_list[i_device]] = 1.0
            feed_dict[model.keep_prob_decoder_pl_list[i_device]] = 1.0
            feed_dict[model.keep_prob_embedding_pl_list[i_device]] = 1.0

        labels_pred_list = session.run(decode_ops, feed_dict=feed_dict)
        for i_device in range(len(labels_pred_list)):
            for i_batch in range(len(inputs[i_device])):

                # Convert from list of index to string
                if is_test:
                    str_true = labels_true[i_device][i_batch][0]
                    # NOTE: transcript is seperated by space('_')
                else:
                    str_true = idx2char(
                        labels_true[i_device][i_batch][1:labels_seq_len[i_device][i_batch] - 1])
                str_pred = idx2char(
                    labels_pred_list[i_device][i_batch]).split('>')[0]
                # NOTE: Trancate by <EOS>

                # Remove garbage labels
                str_true = re.sub(r'[_NZー・<>]+', '', str_true)
                str_pred = re.sub(r'[_NZー・<>]+', '', str_pred)

                # Compute CER
                cer_mean += compute_cer(str_pred=str_pred,
                                        str_true=str_true,
                                        normalize=True)

                if progressbar:
                    pbar.update(1)

        if is_new_epoch:
            break

    cer_mean /= len(dataset)

    # Register original batch size
    if eval_batch_size is not None:
        dataset.batch_size = batch_size_original

    return cer_mean
