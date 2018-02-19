#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import unittest

sys.path.append(os.path.abspath('../../../../'))
from experiments.timit.data.load_dataset_multitask_ctc import Dataset
from utils.io.labels.character import Idx2char
from utils.io.labels.phone import Idx2phone
from utils.measure_time_func import measure_time


class TestLoadDatasetMultitaskCTC(unittest.TestCase):

    def test(self):

        # data_type
        self.check(label_type_main='character', data_type='train')
        self.check(label_type_main='character', data_type='dev')
        self.check(label_type_main='character', data_type='test')

        # label_type
        self.check(label_type_main='character')
        self.check(label_type_main='character_capital_divide')

        # sort
        self.check(label_type_main='character', sort_utt=True)
        self.check(label_type_main='character', sort_utt=True,
                   sort_stop_epoch=2)
        self.check(label_type_main='character', shuffle=True)

        # frame stacking
        self.check(label_type_main='character', frame_stacking=True)

        # splicing
        self.check(label_type_main='character', splice=11)

    @measure_time
    def check(self, label_type_main, data_type='dev',
              shuffle=False, sort_utt=False, sort_stop_epoch=None,
              frame_stacking=False, splice=1):

        print('========================================')
        print('  label_type_main: %s' % label_type_main)
        print('  data_type: %s' % data_type)
        print('  shuffle: %s' % str(shuffle))
        print('  sort_utt: %s' % str(sort_utt))
        print('  sort_stop_epoch: %s' % str(sort_stop_epoch))
        print('  frame_stacking: %s' % str(frame_stacking))
        print('  splice: %d' % splice)
        print('========================================')

        num_stack = 3 if frame_stacking else 1
        num_skip = 3 if frame_stacking else 1
        dataset = Dataset(
            data_type=data_type,
            label_type_main=label_type_main, label_type_sub='phone61',
            batch_size=64, max_epoch=2, splice=splice,
            num_stack=num_stack, num_skip=num_skip,
            shuffle=shuffle,
            sort_utt=sort_utt, sort_stop_epoch=sort_stop_epoch,
            progressbar=True)

        print('=> Loading mini-batch...')
        idx2char = Idx2char(
            map_file_path='../../metrics/mapping_files/' + label_type_main + '.txt')
        idx2phone = Idx2phone(
            map_file_path='../../metrics/mapping_files/phone61.txt')

        for data, is_new_epoch in dataset:
            inputs, labels_char, labels_phone, inputs_seq_len, input_names = data

            if data_type != 'test':
                str_true_char = idx2char(labels_char[0][0])
                str_true_phone = idx2phone(labels_phone[0][0])
            else:
                str_true_char = labels_char[0][0][0]
                str_true_phone = labels_phone[0][0][0]

            print('----- %s ----- (epoch: %.3f)' %
                  (input_names[0][0], dataset.epoch_detail))
            print(str_true_char)
            print(str_true_phone)


if __name__ == '__main__':
    unittest.main()
