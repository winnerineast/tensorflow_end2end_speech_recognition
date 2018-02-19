#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Load dataset for the multitask CTC model (TIMIT corpus).
   In addition, frame stacking and skipping are used.
   You can use only the single GPU version.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from os.path import join, isfile
import pickle
import numpy as np

from utils.dataset.multitask_ctc import DatasetBase


class Dataset(DatasetBase):

    def __init__(self, data_type, label_type_main, label_type_sub,
                 batch_size, max_epoch=None, splice=1,
                 num_stack=1, num_skip=1,
                 shuffle=False, sort_utt=False, sort_stop_epoch=None,
                 progressbar=False):
        """A class for loading dataset.
        Args:
            data_type (string): train or dev or test
            label_type_main (string): character or character_capital_divide
            label_type_sub (stirng): phone39 or phone48 or phone61
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
        """
        super(Dataset, self).__init__()

        self.is_test = True if data_type == 'test' else False

        self.data_type = data_type
        self.label_type_main = label_type_main
        self.label_type_sub = label_type_sub
        self.batch_size = batch_size
        self.max_epoch = max_epoch
        self.splice = splice
        self.num_stack = num_stack
        self.num_skip = num_skip
        self.shuffle = shuffle
        self.sort_utt = sort_utt
        self.sort_stop_epoch = sort_stop_epoch
        self.progressbar = progressbar
        self.num_gpu = 1

        # paths where datasets exist
        dataset_root = ['/data/inaguma/timit',
                        '/n/sd8/inaguma/corpus/timit/dataset']

        input_path = join(dataset_root[0], 'inputs', data_type)
        # NOTE: ex.) save_path: timit_dataset_path/inputs/data_type/***.npy
        label_main_path = join(
            dataset_root[0], 'labels', data_type, label_type_main)
        label_sub_path = join(
            dataset_root[0], 'labels', data_type, label_type_sub)
        # NOTE: ex.) save_path:
        # timit_dataset_path/labels/data_type/label_type/***.npy

        # Load the frame number dictionary
        if isfile(join(input_path, 'frame_num.pickle')):
            with open(join(input_path, 'frame_num.pickle'), 'rb') as f:
                self.frame_num_dict = pickle.load(f)
        else:
            dataset_root.pop(0)
            input_path = join(dataset_root[0], 'inputs', data_type)
            label_main_path = join(
                dataset_root[0], 'labels', data_type, label_type_main)
            label_sub_path = join(
                dataset_root[0], 'labels', data_type, label_type_sub)
            with open(join(input_path, 'frame_num.pickle'), 'rb') as f:
                self.frame_num_dict = pickle.load(f)

        # Sort paths to input & label
        axis = 1 if sort_utt else 0
        frame_num_tuple_sorted = sorted(self.frame_num_dict.items(),
                                        key=lambda x: x[axis])
        input_paths, label_main_paths, label_sub_paths = [], [], []
        for input_name, frame_num in frame_num_tuple_sorted:
            input_paths.append(join(input_path, input_name + '.npy'))
            label_main_paths.append(join(label_main_path, input_name + '.npy'))
            label_sub_paths.append(join(label_sub_path,  input_name + '.npy'))
        if len(label_main_paths) != len(label_sub_paths):
            raise ValueError('The numbers of labels between ' +
                             'character and phone are not same.')
        self.input_paths = np.array(input_paths)
        self.label_main_paths = np.array(label_main_paths)
        self.label_sub_paths = np.array(label_sub_paths)
        # NOTE: Not load dataset yet

        self.rest = set(range(0, len(self.input_paths), 1))
