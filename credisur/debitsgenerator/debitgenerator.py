from .errornotification import ErrorNotification

from .readdebitsexcel import read_debits_excel

from .parsers import parse_debits_headers
from .parsers import parse_debits_lines

from .validators import validate_headers
from .validators import validate_lines

from .notifyerrors import notify_errors


def generate_debits(cwd):

    for notification in execute_generation(cwd):
        if notification.has_errors():
            notify_errors(notification)
            return

    pass

def execute_generation(cwd):
    # leer excel (definir nombre)

    # checkear si están disponibles todos los datos de las cabeceras
    # arrojar errores si falta algo

    # procesar filas de excel

    # checkear si están disponibles todos los datos de las filas
    # arrojar errores si falta algo

    notification = ErrorNotification()

    excel_path = cwd + "/generar_debitos.xlsx"

    raw_data = read_debits_excel(excel_path)

    # procesar cabeceras de excel

    header_data = parse_debits_headers(raw_data) # a collection of headers per debit account

    validate_headers(header_data, notification)

    yield notification

    debits_data = parse_debits_lines(raw_data) # a collection of debit lines per debit account

    validate_lines(debits_data, notification)

    yield notification

    # output
    # for debits page:
    # file_headers = build_file_headers(header_data)
    # file_lines = build_

    # contruir cabeceras de txt

    # construir líneas (cabeceras + filas)

    # construir último registro


    # guardar archivos separados por cuenta