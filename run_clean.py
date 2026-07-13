import os
import sys
import json

# Force run on clean dataset
sys.argv = ['run_all.py', r'e:\AEIA\sample_data\aeia_clean_engine_dataset.csv']

import run_all
