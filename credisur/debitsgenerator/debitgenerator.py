from .errornotification import ErrorNotification

from .filenamebuilder import build_file_name

from .readdebitsexcel import read_debits_excel

from .parsers import (
    parse_debits_headers, parse_debits_lines,
    calculate_last_line
)

from .validators import (
    validate_headers, validate_lines
)

from .notifyerrors import notify_errors

from .writers import (
    stream_headers, stream_lines,
    stream_last_line
)


def generate_debits(cwd):

    for notification in execute_generation(cwd):
        if notification.has_errors():
            notify_errors(notification)
            return


def execute_generation(cwd):
    notification = ErrorNotification()

    excel_path = cwd + "/generar_debitos.xlsx"

    raw_data = read_debits_excel(excel_path)

    # procesar cabeceras de excel
    for page_data in raw_data:

        header_data = parse_debits_headers(page_data)

        notification.collect_notifications(validate_headers(header_data))

        yield notification

        debits_data = parse_debits_lines(page_data)

        notification.collect_notifications(validate_lines(debits_data))

        yield notification

        last_line = calculate_last_line(header_data, debits_data)

        filename = build_file_name(cwd, header_data)

        with open(filename, 'w') as file_stream:
            stream_headers(header_data, file_stream)
            stream_lines(debits_data, file_stream)
            stream_last_line(last_line, file_stream)
