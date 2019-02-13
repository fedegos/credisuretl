
def stream_lines(header_data, debits_data, stream):
    for line in parse_lines(header_data, debits_data):
        stream.write(line)


def parse_lines(header_data, debits_data):
    return []


def stream_last_line(last_line, stream):
    line = parse_last_line(last_line)

    if not line:
        return

    stream.write(line)


def parse_last_line(last_line):
    pass