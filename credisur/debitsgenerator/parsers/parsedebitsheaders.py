

def parse_debits_headers(page_data):
    headers_mapping = map_headers(page_data)
    return Header(page_data.title, headers_mapping)

def map_headers(page_data):
    return {
        'cuit': page_data['B1'].value,
        'prestacion': page_data['B2'].value,
        'ref_debito': page_data['B3'].value,
        'primer_vencimiento': page_data['B4'].value,
        'fecha_proceso': page_data['B5'].value,
    }

class Header:

    def __init__(self, sheet_name, headers_map):
        self._sheet_name = sheet_name
        self._cuit = headers_map['cuit']
        self._prestacion = headers_map['prestacion']
        self._ref_debito = headers_map['ref_debito']
        self._primer_vencimiento = headers_map['primer_vencimiento']
        self._fecha_proceso = headers_map['fecha_proceso']


    @property
    def sheet_name(self):
        return self._sheet_name

    @property
    def cuit(self):
        return self._cuit

    @property
    def prestacion(self):
        return self._prestacion

    @property
    def ref_debito(self):
        return self._ref_debito

    @property
    def primer_vencimiento(self):
        return self._primer_vencimiento

    @property
    def fecha_proceso(self):
        return self._fecha_proceso