

def parse_debits_lines(page_data):
    last_row = page_data.max_row + 1

    debit_lines = []

    for line_num in range(8, last_row):
        line_mapping = map_line(line_num, page_data)
        debit_lines.append(DebitLine(line_mapping))

    return debit_lines


def map_line(row, page_data):
    return {
        'tipo_novedad': page_data.cell(row=row, column=1).value,
        'cbu_bloque_1':  page_data.cell(row=row, column=2).value,
        'cbu_bloque_2': page_data.cell(row=row, column=3).value,
        'id_cliente': page_data.cell(row=row, column=4).value,
        'monto': page_data.cell(row=row, column=5).value,
    }

class DebitLine:

    def __init__(self, line_mapping):
        pass