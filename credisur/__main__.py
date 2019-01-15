import argparse
import os
import sys
import time
from datetime import datetime
import pkg_resources

from functools import reduce

import credisur.dateintelligence as dateintelligence
import credisur.exceladapter as exceladapter
import credisur.excelbuilder as excelbuilder
import credisur.tableextraction as tableextraction

from credisur.config import \
    get_columns_configuration, \
    get_advance_payments_columns, \
    get_last_payment_columns, \
    get_no_payment_due_columns, \
    get_bank_debit_columns

from credisur.extractors import \
    customer_row_extractor, \
    collection_row_extractor, CollectionsExtractorResults, \
    bill_row_extractor, BillExtractorResults, \
    account_receivable_extractor, AccountReceivableExtractorResults

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

    input_customers_filename = inputs_path + 'Clientes.xlsx'
    input_collections_filename = inputs_path + 'Cobranza.xlsx'
    input_pending_bills_filename = inputs_path + 'Factura.xlsx'
    input_accounts_to_collect_filename = inputs_path + 'Cuentas a Cobrar.xlsx'

    upgrade_if_older_version(input_customers_filename)
    upgrade_if_older_version(input_collections_filename)
    upgrade_if_older_version(input_pending_bills_filename)
    upgrade_if_older_version(input_accounts_to_collect_filename)

    # ExcelReader debería tomar un Stream en vez de un filename - TODO: probar

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

    acc_rec_extractor = tableextraction.DataExtractor(
        input_accounts_to_collect_filename,
        'hoja1',
        AccountReceivableExtractorResults(
            customers, bills,
            calendar_ops, first_day_of_current_month, last_date_of_month,
            collections, collections_for_customers,
            list_of_advance_payments, customers_without_payments_due, customers_in_last_payment
        ),
        account_receivable_extractor
    )

    account_receivable_results = acc_rec_extractor.extract()
    accounts_to_collect = account_receivable_results.get_accounts_to_collect()
    errors = errors + account_receivable_results.get_errors()


    all_customers_with_collection = set(
        list(
            map(
                lambda line: line['customer'],
                reduce(
                    lambda memo, item: memo + item,
                    map(
                        lambda x: x[1],
                        accounts_to_collect.items()
                    )
                )
            )
        )
    )

    for customername, customerdetails in customers.items():
        if not customername in collections_for_customers:
            continue

        if not customername in all_customers_with_collection:
            customers_in_last_payment.append({
                "city": customerdetails['city'],
                "customer": customername,
                "address": customerdetails['address'] or 'Sin dirección',
                "lastcollection": "No disponible",
                "reason": "Sin compras abiertas"
            })

    for error in errors:
        print("ADVERTENCIA:", error)

    sorted_accounts_C = sorted(accounts_to_collect['C'],
                               key=lambda x: (x['city'], x['customer'], x['order'], x['due_date_datetime']))

    sorted_accounts_D = sorted(accounts_to_collect['D'],
                               key=lambda x: (x['city'], x['customer'], x['order'], x['due_date_datetime']))
    sorted_accounts_D_H = filter(lambda x: x['person'] == 'H', sorted_accounts_D)
    sorted_accounts_D_F = filter(lambda x: x['person'] == 'F', sorted_accounts_D)

    def convert_amounts_to_bank_format(receivables):
        result = []

        for receivable in receivables:
            receivable['amount'] = str(round(receivable['amount'] * 100)).zfill(8)
            result.append(receivable)

        return result


    def aggregate_amounts_to_collect(receivables):
        result = {}

        for receivable in receivables:
            customer = receivable['customer']
            amount = receivable['amount_to_collect']

            if not customer in result:
                '''
                CBU Bloque 1 - surge de la planilla de clientes (CBU)
                CBU Bloque 2 - surge de la planilla de clientes (CBU)
                Identificación del cliente - nombre del cliente. Surge de las cuentas a cobrar.
                Ref. del Crédito? Fijo por cuenta? Tal vez vaya a Datos a generar por el script sin el Excel.
                Importe (8 enteros + dos decimales sin coma) - suma de monto a cobrar. Surge de las cuentas a cobrar.
                '''

                cbu = customers[customer]['cbu']

                cbu1 = cbu[0:7]
                cbu2 = cbu[7:]
                ref_credit = None

                result[customer] = {}
                result[customer]['event_type'] = 'D'
                result[customer]['customer'] = customer
                result[customer]['cbu1'] = cbu1
                result[customer]['cbu2'] = cbu2
                result[customer]['ref_credit'] = ref_credit
                result[customer]['amount'] = 0

            result[customer]['amount'] += amount

        result = list(result.values())
        result = convert_amounts_to_bank_format(result)

        return result

    receivables_aggregated_by_customer_D_H = aggregate_amounts_to_collect(sorted_accounts_D_H)
    receivables_aggregated_by_customer_D_F = aggregate_amounts_to_collect(sorted_accounts_D_F)

    # print(receivables_aggregated_by_customer_D_H)
    # print(receivables_aggregated_by_customer_D_F)

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

    bank_columns_config = get_bank_debit_columns()

    bank_debit_builder_DH = excelbuilder.BasicBuilder(receivables_aggregated_by_customer_D_H, bank_columns_config)
    collections_excelwriter.build_sheet('Banco Horacio', bank_debit_builder_DH.build_sheet_data())

    bank_debit_builder_DF = excelbuilder.BasicBuilder(receivables_aggregated_by_customer_D_F, bank_columns_config)
    collections_excelwriter.build_sheet('Banco Facundo', bank_debit_builder_DF.build_sheet_data())

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
