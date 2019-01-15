def customer_row_extractor(results, unpacker):
    result = dict()

    name = unpacker.get_value_at(1)

    result['address'] = unpacker.get_value_at(8)
    result['city'] = unpacker.get_value_at(29)
    result['phone'] = unpacker.get_value_at(12)
    result['cbu'] = unpacker.get_value_at(5)

    results[name] = result