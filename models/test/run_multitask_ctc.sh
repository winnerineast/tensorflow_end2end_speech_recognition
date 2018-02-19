#!/bin/bash

# Select GPU
if [ $# -ne 1 ]; then
  echo "Error: set GPU index." 1>&2
  echo "Usage: ./run_multitask_ctc.sh gpu_index" 1>&2
  exit 1
fi

# Set path to CUDA
export PATH=$PATH:/usr/local/cuda-8.0/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda-8.0/lib64:/usr/local/cuda-8.0/extras/CUPTI/lib64

# Set path to python
PYTHON=/home/lab5/inaguma/.pyenv/versions/anaconda3-4.1.1/bin/python

gpu_index=$1

CUDA_VISIBLE_DEVICES=$gpu_index $PYTHON test_multitask_ctc.py
