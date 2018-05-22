import argparse
import os
import sys
import time
from datetime import datetime
from functools import reduce

import credisur.datastructures as datastructures
import credisur.dateintelligence as dateintelligence
import credisur.exceladapter as exceladapter
import credisur.excelbuilder as excelbuilder
import credisur.tableextraction as tableextraction


# TODO: Copiar listado de facturas en solapa.
# TODO: Controlar consistencia código (por ejemplo, D-E está mal.
# TODO: Resolver punitorio


def working_directory():
    return os.getcwd().replace('\\', '/')

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "No es una fecha válida: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

def get_parser():
    parser = argparse.ArgumentParser(description='Script para procesar planillas de Credisur')
    parser.add_argument("--inputs", "-i", help="Permite definir la carpeta de inputs", default="inputs")
    parser.add_argument("--outputs", "-o", help="Permite definir la carpeta de outputs", default="outputs")
    parser.add_argument(
        "--date","-d",
        help="Permite definir la fecha de cálculo para vencimientos. Formato: AAAA-MM-DD. Si no se especifica, toma la fecha de hoy.",
        type=valid_date
    )

    return parser


def is_code_permitted(code):
    print(code)
    return True


def main(args=None):
    PAYMENT_ERRORS = []

    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    cwd = working_directory()

    parser = get_parser()
    params = parser.parse_args(args)

    inputs_path = "%s/%s/" % (cwd, params.inputs)
    outputs_path = "%s/%s/" % (cwd, params.outputs)

    # abrir archivos
    NUEVO = "nuevo"
    HISTORICO = "histórico"

    calendar_ops = dateintelligence.CalendarOperations()

    # calendar
    current_date = params.date or datetime.now()
    first_day_of_current_month = datetime(current_date.year, current_date.month, 1)
    last_date_of_month = calendar_ops.last_day_of_month(current_date)

    def get_version_from_code(code):
        if "de" in code.split("-")[3]:
            return HISTORICO
        return NUEVO

    def get_columns_configuration():
        config_list = list()
        config_list.append(("A", "Ciudad", 'city'))
        config_list.append(("B", "Cliente", 'customer'))
        config_list.append(("C", "Dirección", 'address'))
        config_list.append(("D", "Teléfono", 'phone'))

        config_list.append(("E", "Fecha de Compra", 'date_of_purchase'))
        config_list.append(("F", "Fecha de Vencimiento", 'due_date'))
        config_list.append(("G", "Valor de compra", 'total_purchase_value'))

        config_list.append(("H", "Orden de Compra", 'order'))
        config_list.append(("I", "Última Cobranza", 'last_collection'))

        config_list.append(("J", "Cuotas", 'plan'))
        config_list.append(("K", "Saldo Total", 'debt_balance'))
        config_list.append(("L", "Cuotas a pagar", 'current_payment'))
        config_list.append(("M", "Valor de cuota", 'payment'))
        config_list.append(("N", "Saldo vencido", 'past_due_debt'))  # revisar
        config_list.append(("O", "Deuda impaga a la fecha", 'overdue_balance'))

        config_list.append(("P", "Monto total a cobrar", 'amount_to_collect'))
        return config_list

    def get_old_excel_filename(filename):
        return filename[:-1]

    def upgrade_if_older_version(filename):
        old_filename = get_old_excel_filename(filename)
        if not os.path.isfile(filename) and os.path.isfile(old_filename):
            exceladapter.ExcelUpgrader(old_filename).upgrade()

    errors = []
    collections = datastructures.HashOfLists()
    bills = {}

    customers_in_last_payment = []
    customers_without_payments_due = []

    accounts_to_collect = {
        "C": [],
        "D": [],
        "I": []
    }

    input_customers_filename = inputs_path + 'Clientes.xlsx'
    input_collections_filename = inputs_path + 'Cobranza.xlsx'
    input_pending_bills_filename = inputs_path + 'Factura.xlsx'
    input_accounts_to_collect_filename = inputs_path + 'Cuentas a Cobrar.xlsx'

    upgrade_if_older_version(input_customers_filename)
    upgrade_if_older_version(input_collections_filename)
    upgrade_if_older_version(input_pending_bills_filename)
    upgrade_if_older_version(input_accounts_to_collect_filename)

    collections_reader = exceladapter.excelreader.ExcelReader(input_collections_filename)
    pending_bills_reader = exceladapter.excelreader.ExcelReader(input_pending_bills_filename)
    accounts_to_collect_reader = exceladapter.excelreader.ExcelReader(input_accounts_to_collect_filename)

    collections_sheet = collections_reader.get_sheet('hoja1')
    pending_bills_sheet = pending_bills_reader.get_sheet('hoja1')
    accounts_to_collect_sheet = accounts_to_collect_reader.get_sheet('hoja1')

    def customer_row_extractor(results, unpacker):
        result = dict()

        name = unpacker.get_value_at(1)

        result['address'] = unpacker.get_value_at(8)
        result['city'] = unpacker.get_value_at(28)
        result['phone'] = unpacker.get_value_at(12)

        results[name] = result

    customer_extractor = tableextraction.DataExtractor(
        input_customers_filename,
        'hoja1',
        {},
        customer_row_extractor
    )

    customers = customer_extractor.extract()

    collections_unpacker = tableextraction.TableUnpacker(collections_sheet)

    for row_unpacker in collections_unpacker.read_rows(2):
        collection = dict()

        document = row_unpacker.get_value_at(2)
        raw_code = row_unpacker.get_value_at(5) or ""
        date = row_unpacker.get_value_at(1)
        customer = row_unpacker.get_value_at(3)
        amount = row_unpacker.get_value_at(4)

        version = HISTORICO
        sales_order = ""
        payments = ""

        if "-" in raw_code:
            version = NUEVO
            order_and_payments = raw_code.split("-")
            sales_order, *payments = order_and_payments

        if sales_order and len(sales_order) != 5:
            error = "Cobranza con orden de compra errónea (%s). Documento: %s" % (sales_order, document)
            errors.append(error)

        collection['version'] = version
        collection['date'] = date
        collection['customer'] = customer
        collection['amount'] = amount
        collection['sales_order'] = sales_order
        collection['payments'] = payments

        collections.append(sales_order, collection)

    bills_unpacker = tableextraction.TableUnpacker(pending_bills_sheet)

    for row_unpacker in bills_unpacker.read_rows(2):

        document_type = row_unpacker.get_value_at(3)
        document = row_unpacker.get_value_at(4)

        if document_type == "Factura":
            document_type = "Factura de Venta"

        document_type_and_number = "%s N° %s" % (document_type, document)

        raw_code = row_unpacker.get_value_at(11)
        amount = row_unpacker.get_value_at(18)

        if not raw_code:
            errors.append("Factura sin descripción. Documento: %s" % document)
            continue

        _, _, sales_order, payment_code, *_ = raw_code.split("-")

        if "de" in payment_code:
            continue

        if not sales_order:
            error = "Factura sin orden de compra. Documento: %s" % document
            errors.append(error)
            continue

        version = NUEVO

        if len(sales_order) != 5:
            error = "Factura con orden de compra errónea (%s). Documento: %s" % (sales_order, document)
            errors.append(error)

        if document_type_and_number in bills and version == NUEVO:
            errors.append("Orden de compra repetida. Documento: %s. Orden de compra: %s" % (document, sales_order))
            continue

        bills[document_type_and_number] = amount

    accounts_to_collect_unpacker = tableextraction.TableUnpacker(accounts_to_collect_sheet)

    for row_unpacker in accounts_to_collect_unpacker.read_rows(2):
        account_to_collect = {}

        overdue_balance = 0
        past_due_debt = ""

        document_date = row_unpacker.get_value_at(1)
        due_date = row_unpacker.get_value_at(2)
        document = row_unpacker.get_value_at(3)
        customer = row_unpacker.get_value_at(4)
        raw_code = row_unpacker.get_value_at(9)

        customer_data = customers[customer]

        city = customer_data['city']
        phone = customer_data['phone']
        address = customer_data['address']

        if "Cobranza" in document:
            continue

        if not raw_code:
            continue

        version = get_version_from_code(raw_code)

        if version == HISTORICO and due_date > last_date_of_month:
            continue

        list_of_codes = raw_code.split("-")

        collection_account, collection_person, sales_order, *_ = list_of_codes

        collections_for_order = []
        last_collection_date = "Sin cobranza previa"
        current_payment_number = 1

        if sales_order and sales_order in collections:
            collections_for_order = collections[sales_order]

        if sales_order and len(collections_for_order) > 0:
            last_collection_date = sorted(collections_for_order, key=lambda x: x['date'], reverse=True)[0][
                'date'].strftime(
                "%d/%m/%Y")

        if version == HISTORICO:
            current_payment_number, plan = list_of_codes[3].split(" de ")
            current_payment_number = int(current_payment_number)
            plan = int(plan)
            payment_amount = float(row_unpacker.get_value_at(8))
            total_purchase_value = payment_amount * int(plan)

            debt_balance = ""
            advance_payment = ""

            current_payment_description = str(current_payment_number)

        else:
            if len(list_of_codes) < 5:
                error = "Cuenta a cobrar sin valor de cuota. Documento: %s - Descripción: %s" % (document, raw_code)
                errors.append(error)
                continue

            plan = int(list_of_codes[3])
            payment_amount = float(list_of_codes[4])
            debt_balance = row_unpacker.get_value_at(8)

            total_purchase_value = bills[document]
            paid_amount = total_purchase_value - debt_balance
            advance_payment = total_purchase_value - (plan * payment_amount)

            past_payments = 0

            if total_purchase_value < (plan * payment_amount):
                error = "El monto de venta es menor al plan de pagos. " \
                        "Documento: %s - Valor: %s. Plan: %s - Cuota: %s. Diferencia: %s" % (
                            document, total_purchase_value, plan, payment_amount, advance_payment)
                errors.append(error)
                continue

            if paid_amount > advance_payment:
                past_payments = int((paid_amount - advance_payment) // payment_amount)

            if advance_payment < 0:
                error = "El monto de venta es menor al plan de pagos. " \
                        "Documento: %s - Valor: %s. Plan: %s - Cuota: %s. Diferencia: %s" % (
                            document, total_purchase_value, plan, payment_amount, advance_payment)
                errors.append(error)

            due_dates = calendar_ops.list_of_due_date(due_date, plan)
            due_payments = next((plan - i for i, v in enumerate(reversed(due_dates)) if v < first_day_of_current_month),
                                0)
            due_payments_with_current = next(
                (plan - i for i, v in enumerate(reversed(due_dates)) if v <= last_date_of_month), 0)
            current_payment_number_by_date = current_payment_number = next(
                (plan - i for i, v in enumerate(reversed(due_dates)) if v <= last_date_of_month), 0)
            past_due_debt = advance_payment + (due_payments * payment_amount)
            overdue_balance = past_due_debt - paid_amount

            missing_payments = due_payments_with_current - past_payments

            if not missing_payments > 0:
                customer_without_payment_descrption = "%s - %s (orden: %s) - %s" % (
                    city, customer, sales_order, address or 'Sin dirección')
                customers_without_payments_due.append(customer_without_payment_descrption)
                continue

            missing_payment_numbers = list(current_payment_number_by_date - x for x in range(missing_payments))
            partial_debt_in_payment = overdue_balance % payment_amount

            if partial_debt_in_payment > 0:
                first_payment_description = "+$%s de cuota %s" % (
                    int(partial_debt_in_payment),
                    missing_payment_numbers[-1])
                missing_payment_numbers[-1] = first_payment_description

            current_payment_description = ", ".join(str(i) for i in missing_payment_numbers)

        if plan == current_payment_number:
            customer_details = "%s - %s - %s" % (city, customer, address or 'Sin dirección')
            customers_in_last_payment.append(customer_details)

        document_date_str = document_date.strftime("%d/%m/%Y")
        due_date_str = due_date.strftime("%d/%m/%Y")

        amount_to_collect = float(payment_amount) + float(overdue_balance)

        account_to_collect['version'] = version

        account_to_collect['document'] = document
        account_to_collect['date_of_purchase'] = document_date_str

        account_to_collect['due_date_datetime'] = due_date
        account_to_collect['due_date'] = due_date_str

        account_to_collect['customer'] = customer

        account_to_collect['city'] = city
        account_to_collect['address'] = address
        account_to_collect['phone'] = phone

        account_to_collect['account'] = collection_account
        account_to_collect['person'] = collection_person

        account_to_collect['order'] = sales_order

        account_to_collect['last_collection'] = last_collection_date
        account_to_collect['total_purchase_value'] = total_purchase_value
        account_to_collect['plan'] = plan
        account_to_collect['advance_payment'] = advance_payment
        account_to_collect['debt_balance'] = debt_balance

        account_to_collect['current_payment'] = current_payment_description
        account_to_collect['payment'] = payment_amount
        account_to_collect['past_due_debt'] = past_due_debt
        account_to_collect['overdue_balance'] = overdue_balance

        account_to_collect['amount_to_collect'] = amount_to_collect

        if not account_to_collect['city'] or not account_to_collect['customer']:
            print("FALTA CIUDAD O CLIENTE:", account_to_collect['city'], account_to_collect['customer'])

        accounts_to_collect[collection_account].append(account_to_collect)

    for error in errors:
        print("ADVERTENCIA:", error)

    sorted_accounts_C = sorted(accounts_to_collect['C'],
                               key=lambda x: (x['city'], x['customer'], x['order'], x['due_date_datetime']))

    sorted_accounts_D = sorted(accounts_to_collect['D'],
                               key=lambda x: (x['city'], x['customer'], x['order'], x['due_date_datetime']))
    sorted_accounts_D_H = filter(lambda x: x['person'] == 'H', sorted_accounts_D)
    sorted_accounts_D_F = filter(lambda x: x['person'] == 'F', sorted_accounts_D)

    sorted_accounts_I = sorted(accounts_to_collect['I'],
                               key=lambda x: (x['city'], x['customer'], x['order'], x['due_date_datetime']))

    # crear excel de cobranzas
    collections_filename = outputs_path + 'cuentas_a_cobrar_' + time.strftime("%Y%m%d-%H%M%S") + '.xlsx'
    collections_excelwriter = exceladapter.ExcelWriter(collections_filename)

    columns_config = get_columns_configuration()

    collections_builder_C = excelbuilder.BasicBuilder(sorted_accounts_C, columns_config)
    collections_excelwriter.build_sheet("Créditos", collections_builder_C.build_sheet_data())

    collections_builder_DH = excelbuilder.BasicBuilder(sorted_accounts_D_H, columns_config)
    collections_excelwriter.build_sheet('Débitos Horacio', collections_builder_DH.build_sheet_data())

    collections_builder_DF = excelbuilder.BasicBuilder(sorted_accounts_D_F, columns_config)
    collections_excelwriter.build_sheet('Débitos Facundo', collections_builder_DF.build_sheet_data())

    collections_builder_I = excelbuilder.BasicBuilder(sorted_accounts_I, columns_config)
    collections_excelwriter.build_sheet('ICBC', collections_builder_I.build_sheet_data())

    collections_excelwriter.save()

    errors_filename = outputs_path + 'errors_' + time.strftime("%Y%m%d-%H%M%S") + '.txt'
    with open(errors_filename, 'w') as f:
        for error in errors:
            f.write(error)
            f.write("\n")

    last_payment_filename = outputs_path + 'última_cuota_' + time.strftime("%Y%m%d-%H%M%S") + '.txt'
    with open(last_payment_filename, 'w') as f:
        for customer in sorted(customers_in_last_payment):
            f.write(customer)
            f.write("\n")

    no_payment_due_filename = outputs_path + 'clientes_sin_pagos_' + time.strftime("%Y%m%d-%H%M%S") + '.txt'
    with open(no_payment_due_filename, 'w') as f:
        for customer in sorted(customers_without_payments_due):
            f.write(customer)
            f.write("\n")

    for payment_error in PAYMENT_ERRORS:
        print(payment_error)


if __name__ == "__main__":
    main()
