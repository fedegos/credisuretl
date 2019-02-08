from .errornotification import ErrorNotification
from .parsedebitsheaders import parse_debits_headers
from .validators import validate_headers


def generate_debits(cwd):
    # leer excel (definir nombre)

    '''
    notification = ErrorNotification()

    excel_path = cwd + "/generar_debitos.xlsx"

    raw_data = read_debits_excel(excel_path)

    # procesar cabeceras de excel

    header_data = parse_debits_headers(raw_data)

    validate_headers(header_data, notification)

    if notification.has_errors():
        notify_errors(notification)
        return

    '''



    # checkear si están disponibles todos los datos de las cabeceras
    # arrojar errores si falta algo

    # procesar filas de excel

    # checkear si están disponibles todos los datos de las filas
    # arrojar errores si falta algo

    # contruir cabeceras de txt

    # construir líneas (cabeceras + filas)

    # construir último registro


    # guardar archivos separados por cuenta

    pass

