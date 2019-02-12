
def stream_headers(header_data, stream):
    line = parse_header(header_data)
    stream.write(line)


def parse_header(header_data):
    pass


def stream_lines(debits_data, stream):
    for line in parse_lines(debits_data):
        stream.write(line)


def parse_lines(debits_data):
    pass


def stream_last_line(last_line, stream):
    line = parse_last_line(last_line)
    stream.write(line)


def parse_last_line(last_line):
    pass