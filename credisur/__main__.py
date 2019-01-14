import argparse
import os
import sys
import time
from datetime import datetime
import pkg_resources

import credisur.datastructures as datastructures
import credisur.dateintelligence as dateintelligence
import credisur.exceladapter as exceladapter
import credisur.excelbuilder as excelbuilder
import credisur.tableextraction as tableextraction

from credisur.config import \
    get_columns_configuration, \
    get_advance_payments_columns, \
    get_last_payment_columns, \
    get_no_payment_due_columns
from credisur.extractors import \
    customer_row_extractor, \
    collection_row_extractor, \
    CollectionsExtractorResults, \
    bill_row_extractor, \
    BillExtractorResults

from credisur.models import AccountReceivable, Collection, Collections

from credisur.bankparser import parse_bank_files

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

    parser.add_argument("--version", "-v", help="Muestra la versión.", action="store_true")

    parser.add_argument("--banco", "-b", help="Procesa los archivos del banco disponibles en la carpeta.",
                        action="store_true")

    parser.add_argument("--inputs", "-i", help="Permite definir la carpeta de inputs", default="inputs")
    parser.add_argument("--outputs", "-o", help="Permite definir la carpeta de outputs", default="outputs")
    parser.add_argument(
        "--date","-d",
        help="Permite definir la fecha de cálculo para vencimientos. Formato: AAAA-MM-DD. Si no se especifica, toma la fecha de hoy.",
        type=valid_date
    )

    return parser


def is_code_permitted(code):
    return True


def main(args=None):
    PAYMENT_ERRORS = []

    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    cwd = working_directory()

    parser = get_parser()
    params = parser.parse_args(args)

    if params.version:
        print(pkg_resources.require("credisuretl")[0].version)
        return

    if params.banco:
        parse_bank_files(cwd)
        return

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

    def get_old_excel_filename(filename):
        return filename[:-1]

    def upgrade_if_older_version(filename):
        old_filename = get_old_excel_filename(filename)
        if not os.path.isfile(filename) and os.path.isfile(old_filename):
            exceladapter.ExcelUpgrader(old_filename).upgrade()

    errors = []

    customers_in_last_payment = []
    customers_without_payments_due = []
    list_of_advance_payments = []

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

    # ExcelReader debería tomar un Stream en vez de un filename - TODO: probar
    pending_bills_reader = exceladapter.excelreader.ExcelReader(input_pending_bills_filename)
    accounts_to_collect_reader = exceladapter.excelreader.ExcelReader(input_accounts_to_collect_filename)

    pending_bills_sheet = pending_bills_reader.get_sheet('hoja1')
    accounts_to_collect_sheet = accounts_to_collect_reader.get_sheet('hoja1')

    customer_extractor = tableextraction.DataExtractor(
        input_customers_filename,
        'hoja1',
        {},
        customer_row_extractor
    )

    customers = customer_extractor.extract()

    collection_extractor = tableextraction.DataExtractor(
        input_collections_filename,
        'hoja1',
        CollectionsExtractorResults(),
        collection_row_extractor
    )

    collection_extraction_results = collection_extractor.extract()

    collections = collection_extraction_results.get_collections()
    collections_for_customers = collection_extraction_results.get_collections_for_customers()
    errors = errors + collection_extraction_results.get_errors()

    for customername, customerdetails in customers.items():
        if not customername in collections_for_customers:
            customers_in_last_payment.append({
                "city": customerdetails['city'],
                "customer": customername,
                "address": customerdetails['address'] or 'Sin dirección',
                "lastcollection": "No disponible",
                "reason": "Sin compras abiertas"
            })

    bill_extractor = tableextraction.DataExtractor(
        input_pending_bills_filename,
        'hoja1',
        BillExtractorResults(),
        bill_row_extractor
    )

    bill_extractor_results = bill_extractor.extract()

    bills = bill_extractor_results.get_bills()
    errors = errors + bill_extractor_results.get_errors()

    accounts_to_collect_unpacker = tableextraction.TableUnpacker(accounts_to_collect_sheet)

    for row_unpacker in accounts_to_collect_unpacker.read_rows(2):

        document_date = row_unpacker.get_value_at(1)
        due_date = row_unpacker.get_value_at(2)
        document = row_unpacker.get_value_at(3)
        customer = row_unpacker.get_value_at(4)
        raw_code = row_unpacker.get_value_at(9)

        if "Cobranza" in document: continue
        if not raw_code: continue
        if len(raw_code.split("-")) < 4: continue

        line_amount = float(row_unpacker.get_value_at(8))
        line_balance = row_unpacker.get_value_at(8)

        customer_data = customers[customer]

        account_receivable = AccountReceivable(document_date, due_date, document,
                                               customer, raw_code, customer_data, line_amount,
                                               line_balance, calendar_ops)

        if not account_receivable.is_historic_and_due_for(last_date_of_month):
            continue

        if not account_receivable.validate_payment_plan(errors):
            continue


        account_receivable.configure_previous_collections(collections, collections_for_customers)
        account_receivable.compute_last_collection_date()


        account_receivable.compute_due_payment(bills, first_day_of_current_month, last_date_of_month)

        account_receivable.validate_low_advance_payment(100, errors)
        account_receivable.validate_advance_payment(errors)

        account_receivable.add_to_list_if_advance_payments(list_of_advance_payments)

        if not account_receivable.validate_total_sale_amount_and_plan_value(errors):
            continue

        if not account_receivable.has_due_payments(customers_without_payments_due):
            continue

        if not account_receivable.validate_person(errors):
            continue

        account_receivable.add_to_list_if_in_last_payment(customers_in_last_payment, first_day_of_current_month)
        account_to_collect = account_receivable.to_dict()

        if not account_to_collect['city'] or not account_to_collect['customer']:
            print("FALTA CIUDAD O CLIENTE:", account_to_collect['city'], account_to_collect['customer'])

        accounts_to_collect[account_to_collect['account']].append(account_to_collect)

    for error in errors:
        print("ADVERTENCIA:", error)

    sorted_accounts_C = sorted(accounts_to_collect['C'],
                               key=lambda x: (x['city'], x['customer'], x['order'], x['due_date_datetime']))

    sorted_accounts_D = sorted(accounts_to_collect['D'],
                               key=lambda x: (x['city'], x['customer'], x['order'], x['due_date_datetime']))
    sorted_accounts_D_H = filter(lambda x: x['person'] == 'H', sorted_accounts_D)
    sorted_accounts_D_F = filter(lambda x: x['person'] == 'F', sorted_accounts_D)

    # print("WRONG PERSON ----- ",list(filter(lambda x: x['person'] not in ['H', 'F'], sorted_accounts_D)))

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

    last_payment_filename = outputs_path + 'última_cuota_' + time.strftime("%Y%m%d-%H%M%S") + '.xlsx'

    last_payment_composer = exceladapter.ExcelBasicComposer(
        last_payment_filename,
        customers_in_last_payment,
        get_last_payment_columns(),
        "Última Cuota"
    )
    last_payment_composer.save()


    no_payment_due_filename = outputs_path + 'ordenes_de_compra_abiertas_sin_cuotas_a_cobrar_este_periodo' + time.strftime(
        "%Y%m%d-%H%M%S") + '.xlsx'

    no_payment_due_composer = exceladapter.ExcelBasicComposer(
        no_payment_due_filename,
        customers_without_payments_due,
        get_no_payment_due_columns(),
        "Sin cuotas"
    )
    no_payment_due_composer.save()

    advance_payments_filename = outputs_path + 'anticipos_' + time.strftime("%Y%m%d-%H%M%S") + '.xlsx'

    advance_payments_composer = exceladapter.ExcelBasicComposer(
        advance_payments_filename,
        list_of_advance_payments,
        get_advance_payments_columns(),
        "Anticipos"
    )
    advance_payments_composer.save()

    errors_filename = outputs_path + 'errors_' + time.strftime("%Y%m%d-%H%M%S") + '.txt'
    with open(errors_filename, 'w') as f:
        for error in errors:
            f.write(error)
            f.write("\n")

    for payment_error in PAYMENT_ERRORS:
        print(payment_error)


if __name__ == "__main__":
    main()
