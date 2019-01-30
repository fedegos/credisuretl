def get_bank_debit_columns():
    config_list = list()
    config_list.append(("A", "Tipo de Novedad", 'event_type'))
    config_list.append(("B", "CBU Bloque 1", 'cbu1'))
    config_list.append(("C", "CBU Bloque 2", 'cbu2'))
    config_list.append(("D", "Identificación del cliente", 'customer'))
    config_list.append(("E", "Ref. del débito", 'ref_credit'))
    config_list.append(("F", "Importe", 'amount'))
    return config_list