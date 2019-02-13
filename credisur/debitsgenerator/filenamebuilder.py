from datetime import datetime

def build_file_name(cwd, header_data):
    filename = cwd + '/../outputs/ORI' + datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3] + '.txt'

    return filename