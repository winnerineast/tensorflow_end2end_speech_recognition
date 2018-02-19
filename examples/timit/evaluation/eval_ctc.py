#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Evaluate the trained CTC model (TIMIT corpus)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from os.path import join, abspath
import sys
import tensorflow as tf
import yaml
import argparse

sys.path.append(abspath('../../../'))
from examples.timit.data.load_dataset_ctc import Dataset
from examples.timit.metrics.ctc import do_eval_per, do_eval_cer
from models.ctc.ctc import CTC

parser = argparse.ArgumentParser()
parser.add_argument('--epoch', type=int, default=-1,
                    help='the epoch to restore')
parser.add_argument('--model_path', type=str,
                    help='path to the model to evaluate')
parser.add_argument('--beam_width', type=int, default=20,
                    help='beam_width (int, optional): beam width for beam search.' +
                    ' 1 disables beam search, which mean greedy decoding.')
parser.add_argument('--eval_batch_size', type=str, default=1,
                    help='the size of mini-batch in evaluation')


def do_eval(model, params, epoch, beam_width, eval_batch_size):
    """Evaluate the model.
    Args:
        model: the model to restore
        params (dict): A dictionary of parameters
        epoch (int): the epoch to restore
        beam_width (int): beam_width (int, optional): beam width for beam search.
            1 disables beam search, which mean greedy decoding.
        eval_batch_size (int): the size of mini-batch when evaluation
    """
    # Load dataset
    if 'phone' in params['label_type']:
        test_data = Dataset(
            data_type='test', label_type='phone39',
            batch_size=eval_batch_size, splice=params['splice'],
            num_stack=params['num_stack'], num_skip=params['num_skip'],
            shuffle=False, progressbar=True)
    else:
        test_data = Dataset(
            data_type='test', label_type=params['label_type'],
            batch_size=eval_batch_size, splice=params['splice'],
            num_stack=params['num_stack'], num_skip=params['num_skip'],
            shuffle=False, progressbar=True)

    # Define placeholders
    model.create_placeholders()

    # Add to the graph each operation (including model definition)
    _, logits = model.compute_loss(model.inputs_pl_list[0],
                                   model.labels_pl_list[0],
                                   model.inputs_seq_len_pl_list[0],
                                   model.keep_prob_pl_list[0])
    decode_op = model.decoder(logits,
                              model.inputs_seq_len_pl_list[0],
                              beam_width=beam_width)
    per_op = model.compute_ler(decode_op, model.labels_pl_list[0])

    # Create a saver for writing training checkpoints
    saver = tf.train.Saver()

    with tf.Session() as sess:
        ckpt = tf.train.get_checkpoint_state(model.save_path)

        # If check point exists
        if ckpt:
            # Use last saved model
            model_path = ckpt.model_checkpoint_path
            if epoch != -1:
                # Use the best model
                # NOTE: In the training stage, parameters are saved only when
                # accuracies are improved
                model_path = model_path.split('/')[:-1]
                model_path = '/'.join(model_path) + '/model.ckpt-' + str(epoch)
            saver.restore(sess, model_path)
            print("Model restored: " + model_path)
        else:
            raise ValueError('There are not any checkpoints.')

        print('Test Data Evaluation:')
        if 'char' in params['label_type']:
            cer_test, wer_test = do_eval_cer(
                session=sess,
                decode_op=decode_op,
                model=model,
                dataset=test_data,
                label_type=params['label_type'],
                is_test=True,
                eval_batch_size=eval_batch_size,
                progressbar=True)
            print('  CER: %f %%' % (cer_test * 100))
            print('  WER: %f %%' % (wer_test * 100))
        else:
            per_test = do_eval_per(
                session=sess,
                decode_op=decode_op,
                per_op=per_op,
                model=model,
                dataset=test_data,
                label_type=params['label_type'],
                is_test=True,
                eval_batch_size=eval_batch_size,
                progressbar=True)
            print('  PER: %f %%' % (per_test * 100))


def main():

    args = parser.parse_args()

    # Load config file
    with open(join(args.model_path, 'config.yml'), "r") as f:
        config = yaml.load(f)
        params = config['param']

    # Except for a blank label
    if params['label_type'] == 'phone61':
        params['num_classes'] = 61
    elif params['label_type'] == 'phone48':
        params['num_classes'] = 48
    elif params['label_type'] == 'phone39':
        params['num_classes'] = 39
    elif params['label_type'] == 'character':
        params['num_classes'] = 28
    elif params['label_type'] == 'character_capital_divide':
        params['num_classes'] = 72
    else:
        raise TypeError

    # Model setting
    model = CTC(encoder_type=params['encoder_type'],
                input_size=params['input_size'],
                splice=params['splice'],
                num_stack=params['num_stack'],
                num_units=params['num_units'],
                num_layers=params['num_layers'],
                num_classes=params['num_classes'],
                lstm_impl=params['lstm_impl'],
                use_peephole=params['use_peephole'],
                parameter_init=params['weight_init'],
                clip_grad_norm=params['clip_grad_norm'],
                clip_activation=params['clip_activation'],
                num_proj=params['num_proj'],
                weight_decay=params['weight_decay'])

    model.save_path = args.model_path
    do_eval(model=model, params=params,
            epoch=args.epoch, eval_batch_size=args.eval_batch_size,
            beam_width=args.beam_width)


if __name__ == '__main__':
    main()
