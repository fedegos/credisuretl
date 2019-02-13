from .errorsiterator import ErrorsIterator

def validate_lines(debits_data):
    errors = ErrorsIterator()

    map_func = validate_line_func(errors)

    map(map_func, debits_data)

    return errors

def validate_line_func(errors):

    def validate_line(line):
        """

        :type line: credisur.debitsgenerator.parsers.parsedebitslines.DebitLine
        """

        row = line.row
        sheet_name = line.sheet_name

        def add_error(error):
            errors.add_error(error + " en fila %s de solapa %s" % (row, sheet_name))

        if not line.tipo_novedad:
            add_error("Falta el 'Tipo Novedad'")

        if not line.cbu_bloque_1:
            add_error("Falta el 'CBU Bloque 1'")

        if not line.cbu_bloque_2:
            add_error("Falta el 'CBU Bloque 2'")

        if not line.id_cliente:
            add_error("Falta el 'ID Cliente'")

        if not line.monto:
            add_error("Falta el 'Monto'")

    return validate_line
