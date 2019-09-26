def customer_row_extractor(results, unpacker):
    result = dict()

    name = unpacker.get_value_at(1)

    result['address'] = unpacker.get_value_at(8)
    result['city'] = unpacker.get_value_at(33) # Cambio de Xubio 2019 09 (de 33 a 32) - 2do cambio en 2019 09 (de 32 a 33)
    result['phone'] = unpacker.get_value_at(12)
    result['cbu'] = unpacker.get_value_at(6) # Cambio de Xubio 2019 09 (de 5 a 6)

    results[name] = result