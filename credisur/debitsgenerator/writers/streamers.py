
def stream_lines(header_data, debits_data, stream):
    for line in parse_lines(header_data, debits_data):
        stream.write(line + "\n")


def parse_lines(header_data, debits_data):
    func_to_map = build_map_func(header_data)
    return map(func_to_map, debits_data)


def build_map_func(header_data):
    """

    :type header_data: credisur.debitsgenerator.parsers.parsedebitsheaders.Header
    """

    def build_string_for(line):
        """

        :type line: credisur.debitsgenerator.parsers.parsedebitslines.DebitLine
        """
        return "%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s" % (
            line.tipo_novedad,
            header_data.cuit,
            " " * 3, # sector
            header_data.prestacion.ljust(10),
            header_data.primer_vencimiento,
            line.cbu_bloque_1,
            " " * 3, # filler
            line.cbu_bloque_2,
            line.id_cliente[:22].ljust(22),
            header_data.primer_vencimiento,
            header_data.ref_debito.ljust(15),
            line.monto,
            "80", # moneda 80 pesos 82 dólares
            " " * 8, # fecha segundo vencimiento
            "0" * 10, # monto segundo vencimiento
            " " * 8,  # fecha tercer vencimiento
            "0" * 10,  # monto tercer vencimiento
            " " * 22, # no corresponde
            " " * 3, # no corresponde
            "0" * 10, # no corresponde
            "0" * 10, # no corresponde
            " " * 54 # FILLER
        )

    return build_string_for

def stream_last_line(last_line, stream):
    line = parse_last_line(last_line)

    if not line:
        return

    stream.write(line)


def parse_last_line(last_line):
    pass