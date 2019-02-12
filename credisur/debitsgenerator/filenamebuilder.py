import time

def build_file_name(cwd, header_data):
    filename = cwd + '/../outputs/ORI' + time.strftime("%Y%m%d-%H%M%S") + '.txt'
    return filename