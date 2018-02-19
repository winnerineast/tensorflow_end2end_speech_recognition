#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Load dataset for the multitask CTC model (CSJ corpus).
   In addition, frame stacking and skipping are used.
   You can use the multi-GPU version.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from os.path import join
import pickle
import numpy as np

from utils.dataset.each_load.multitask_ctc_each_load import DatasetBase


class Dataset(DatasetBase):

    def __init__(self, data_type, train_data_size, label_type_main,
                 label_type_sub, batch_size,
                 max_epoch=None, splice=1,
                 num_stack=1, num_skip=1,
                 shuffle=False, sort_utt=True, sort_stop_epoch=None,
                 progressbar=False, num_gpu=1, is_gpu=True):
        """A class for loading dataset.
        Args:
            data_type (string): train or dev or eval1 or eval2 or eval3
            train_data_size (string): train_subset or train_fullset
            label_type_main (string): label type of the main task
                kanji or kanji_wakachi or kana or kana_wakachi
            label_type_sub (string): label type of the sub task
                kana or kana_wakachi or phone
            batch_size (int): the size of mini-batch
            max_epoch (int, optional): the max epoch. None means infinite loop.
            splice (int, optional): frames to splice. Default is 1 frame.
            num_stack (int, optional): the number of frames to stack
            num_skip (int, optional): the number of frames to skip
            shuffle (bool, optional): if True, shuffle utterances. This is
                disabled when sort_utt is True.
            sort_utt (bool, optional): if True, sort all utterances by the
                number of frames and utteraces in each mini-batch are shuffled.
                Otherwise, shuffle utteraces.
            sort_stop_epoch (int, optional): After sort_stop_epoch, training
                will revert back to a random order
            progressbar (bool, optional): if True, visualize progressbar
            num_gpu (int, optional): if more than 1, divide batch_size by num_gpu
            is_gpu (bool, optional): if True, use dataset in the GPU server. This is
                useful when data size is very large and you cannot load all
                dataset at once. Then, you should put dataset on the GPU server
                you will use to reduce data-communication time between servers.
        """
        super(Dataset, self).__init__()

        if data_type in ['eval1', 'eval2', 'eval3'] and label_type_sub != 'phone':
            self.is_test = True
        else:
            self.is_test = False

        self.data_type = data_type
        self.train_data_size = train_data_size
        self.label_type_main = label_type_main
        self.label_type_sub = label_type_sub
        self.batch_size = batch_size * num_gpu
        self.max_epoch = max_epoch
        self.splice = splice
        self.num_stack = num_stack
        self.num_skip = num_skip
        self.shuffle = shuffle
        self.sort_utt = sort_utt
        self.sort_stop_epoch = sort_stop_epoch
        self.progressbar = progressbar
        self.num_gpu = num_gpu
        self.padded_value = -1

        if is_gpu:
            # GPU server
            root = '/data/inaguma/csj'
        else:
            # CPU server
            root = '/n/sd8/inaguma/corpus/csj/dataset'

        input_path = join(root, 'inputs', train_data_size, data_type)
        label_main_path = join(root, 'labels/ctc', train_data_size,
                               label_type_main, data_type)
        label_sub_path = join(root, 'labels/ctc', train_data_size,
                              label_type_sub, data_type)

        # Load the frame number dictionary
        with open(join(input_path, 'frame_num.pickle'), 'rb') as f:
            self.frame_num_dict = pickle.load(f)

        # Sort paths to input & label
        axis = 1 if sort_utt else 0
        frame_num_tuple_sorted = sorted(self.frame_num_dict.items(),
                                        key=lambda x: x[axis])
        input_paths, label_main_paths, label_sub_paths = [], [], []
        for utt_name, frame_num in frame_num_tuple_sorted:
            # ex.) utt_name: speaker + _ + utt_index
            input_paths.append(join(input_path, utt_name + '.npy'))
            label_main_paths.append(join(label_main_path, utt_name + '.npy'))
            label_sub_paths.append(join(label_sub_path, utt_name + '.npy'))
        self.input_paths = np.array(input_paths)
        self.label_main_paths = np.array(label_main_paths)
        self.label_sub_paths = np.array(label_sub_paths)
        # NOTE: Not load dataset yet

        self.rest = set(range(0, len(self.input_paths), 1))
