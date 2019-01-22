import sys

import os

from os import listdir
from os.path import isfile, join

import time

def main(args):

    outputs_path = "../outputs"

    '''
    dated_dir_path = join(outputs_path, time.strftime("%Y %m %d"))
    os.mkdir(dated_dir_path)
    '''

    onlyfiles = [f for f in listdir(outputs_path) if isfile(join(outputs_path, f))]
    for file in onlyfiles:
        os.rename(join(outputs_path, file), join(outputs_path, "backups", file))


if __name__ == '__main__':
    main(sys.argv[1:])
