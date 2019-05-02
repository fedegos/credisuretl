import sys

import os
import shutil

from os import listdir
from os.path import isfile, join

import time

def main(args):

    inputs_path = "../inputs"

    dated_dir_path = join(os.getcwd(), inputs_path, "backups", time.strftime("%Y %m %d"))
    
    print(dated_dir_path)

    if(os.path.isdir(dated_dir_path)):
        print("Folder already exists.")
        return

    os.makedirs(dated_dir_path, mode=0o777)

    onlyfiles = [f for f in listdir(inputs_path) if isfile(join(inputs_path, f))]
    for file in onlyfiles:
        print(file)
        shutil.copy(join(inputs_path, file), join(dated_dir_path, file))


if __name__ == '__main__':
    main(sys.argv[1:])
