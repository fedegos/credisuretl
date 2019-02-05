import sys

import os
import shutil

from os import listdir
from os.path import isfile, join

import time

def main(args):

    inputs_path = "../inputs"

    dated_dir_path = join(inputs_path, "backups", time.strftime("%Y %m %d"))

    if(os.path.isdir(dated_dir_path)):
        print("Folder already exists.")
        return

    os.mkdir(dated_dir_path)

    onlyfiles = [f for f in listdir(inputs_path) if isfile(join(inputs_path, f))]
    for file in onlyfiles:
        shutil.copy(join(inputs_path, file), join(dated_dir_path, file))


if __name__ == '__main__':
    main(sys.argv[1:])
