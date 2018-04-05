import openpyxl
import time
# import json
from datetime import datetime
from functools import reduce

import tableextraction
import exceladapter
import translators
import excelbuilder
import datastructures
import dateintelligence

# abrir archivos
NUEVO = "nuevo"
HISTORICO = "histórico"

current_date = datetime.now()


def get_version_from_code(raw_code):
    if "de" in raw_code.split("-")[3]:
        return HISTORICO
    return NUEVO


calendar_ops = dateintelligence.CalendarOperations()

errors = []
customers = {}
collections = datastructures.HashOfLists()
bills = {}
accounts_to_collect = []

customers_reader = exceladapter.excelreader.ExcelReader('inputs/Clientes al 2018-04-03.xlsx')
collections_reader = exceladapter.excelreader.ExcelReader('inputs/Cobranzas al 2018-04-03.xlsx')
pending_bills_reader = exceladapter.excelreader.ExcelReader('inputs/Facturas pendientes de cobro al 2018-04-03.xlsx')
accounts_to_collect_reader = exceladapter.excelreader.ExcelReader('inputs/Cuentas a Cobrar al 2018-04-03 crudo.xlsx')

customers_sheet = customers_reader.get_sheet('Sheet0')
collections_sheet = collections_reader.get_sheet('hoja1')
pending_bills_sheet = pending_bills_reader.get_sheet('hoja1')
accounts_to_collect_sheet = accounts_to_collect_reader.get_sheet('hoja1')

customers_unpacker = tableextraction.TableUnpacker(customers_sheet)

for row_unpacker in customers_unpacker.read_rows(2):
    customer = {}

    name = row_unpacker.get_value_at(1)

    customer['address'] = row_unpacker.get_value_at(8)
    customer['city'] = row_unpacker.get_value_at(28)
    customer['phone'] = row_unpacker.get_value_at(12)

    customers[name] = customer

collections_unpacker = tableextraction.TableUnpacker(collections_sheet)

for row_unpacker in collections_unpacker.read_rows(2):
    collection = {}

    raw_code = row_unpacker.get_value_at(5)

    sales_order = ""

    if "-" in raw_code:
        version = NUEVO
        order_and_payments = raw_code.split("-")
        sales_order = order_and_payments.pop(0)
        payments = order_and_payments
    else:
        payments = ""
        version = HISTORICO

    # Fecha	Comprobante	Cliente	Total	Observaciones
    collection['version'] = version
    collection['date'] = row_unpacker.get_value_at(1)
    collection['customer'] = row_unpacker.get_value_at(3)
    collection['amount'] = row_unpacker.get_value_at(4)
    collection['sales_order'] = sales_order
    collection['payments'] = payments

    collections.append(sales_order, collection)

# print(collections.keys())
'''
for k, v in collections.items():
    print(collections[k])

    if not k:
        print(k)
        print(v)
'''

# de facturas pendientes de cobro sale monto total
# se cruza vía orden de compra

bills_unpacker = tableextraction.TableUnpacker(pending_bills_sheet)

for row_unpacker in bills_unpacker.read_rows(2):

    document = row_unpacker.get_value_at(4)
    raw_code = row_unpacker.get_value_at(11)

    if not raw_code:
        errors.append("Factura sin descripción. Documento: %s" % (document))
        continue

    if "de" in raw_code.split("-")[3]:
        version = HISTORICO
    else:
        version = NUEVO

    if version == HISTORICO:
        continue

    sales_order = raw_code.split("-")[2]

    if not sales_order:
        errors.append("Factura sin orden de compra. Documento: %s" % (document))
        continue

    amount = row_unpacker.get_value_at(18)

    if sales_order in bills and version == NUEVO:
        print(sales_order)
        errors.append("Orden de compra repetida. Documento: %s. Orden de compra: %s" % (document, sales_order))
        continue

    bills[sales_order] = amount

accounts_to_collect_unpacker = tableextraction.TableUnpacker(accounts_to_collect_sheet)

for row_unpacker in accounts_to_collect_unpacker.read_rows(2):

    account_to_collect = {}

    document_date = row_unpacker.get_value_at(1)
    due_date = row_unpacker.get_value_at(2)
    document = row_unpacker.get_value_at(3)
    customer = row_unpacker.get_value_at(4)

    customer_data = customers[customer]

    city = customer_data['city']
    phone = customer_data['phone']
    address = customer_data['address']

    if "Cobranza" in document:
        continue

    raw_code = row_unpacker.get_value_at(9)

    if not raw_code:
        # ya lo toma de las facturas, no debería en un listado sin que esté en el otro
        # errors.append("Cuenta a cobrar sin descripción. Documento: %s" % (document))
        continue

    version = get_version_from_code(raw_code)

    list_of_codes = raw_code.split("-")

    collection_account = list_of_codes[0]
    collection_person = list_of_codes[1]
    sales_order = list_of_codes[2]

    collections_for_order = []
    last_collection_date = "Sin cobranza previa"
    current_payment_number = 1

    if sales_order and sales_order in collections:
        collections_for_order = collections[sales_order]

    if sales_order and len(collections_for_order) > 0:
        last_collection_date = sorted(collections_for_order, key=lambda x: x['date'], reverse=True)[0]['date']

        if version == NUEVO:
            previous_payments = reduce(lambda x, y: x + y, list(map(lambda x: x['payments'], collections_for_order)),
                                       [])
            previous_payments_without_advances_str = filter(lambda x: x != 'E', previous_payments)
            previous_payments_without_advances = [int(x) for x in previous_payments_without_advances_str]
            current_payment_number = max(previous_payments_without_advances, default=0) + 1

    if version == HISTORICO:
        current_payment_number, plan = list_of_codes[3].split(" de ")
        plan = int(plan)
        payment_amount = float(row_unpacker.get_value_at(8))
        total_purchase_value = payment_amount * int(plan)

        debt_balance = ""
        advance_payment = ""

    else:
        if len(list_of_codes) < 5:
            error = "Cuenta a cobrar sin valor de cuota. Documento: %s - Descripción: %s" % (document, raw_code)
            errors.append(error)
            continue

        plan = int(list_of_codes[3])
        payment_amount = float(list_of_codes[4])
        debt_balance = row_unpacker.get_value_at(8)
        total_purchase_value = bills[sales_order]
        paid_amount = total_purchase_value - debt_balance
        advance_payment = total_purchase_value - (plan * payment_amount)

        if (advance_payment < 0):
            error = "El monto de venta es menor al plan de pagos. Documento: %s - Valor: %s. Plan: %s - Cuota: %s. Diferencia: %s" % (
            document, total_purchase_value, plan, payment_amount, advance_payment)
            errors.append(error)

    # TODO: months_from_sale

    last_due_date = calendar_ops.add_months(due_date, plan)

    overdue_balance = ""
    past_due_debt = ""

    if version == NUEVO:
        due_dates = calendar_ops.list_of_due_date(due_date, plan)
        #  i = next(i + 1 for i,v in enumerate(l) if v > 0)
        due_payments = next((plan - i for i, v in enumerate(reversed(due_dates)) if v <= current_date), 0)
        past_due_debt = advance_payment + (due_payments * payment_amount)
        overdue_balance = past_due_debt - paid_amount

    if isinstance(last_collection_date, datetime):
        last_collection_date = last_collection_date.strftime("%d/%m/%Y")

    account_to_collect['version'] = version

    account_to_collect['document'] = document
    account_to_collect['due_date'] = due_date.strftime("%d/%m/%Y")

    account_to_collect['customer'] = customer
    account_to_collect['city'] = city
    account_to_collect['address'] = address

    account_to_collect['account'] = collection_account
    account_to_collect['person'] = collection_person
    account_to_collect['order'] = sales_order

    account_to_collect['last_collection'] = last_collection_date
    account_to_collect['total_purchase_value'] = total_purchase_value
    account_to_collect['plan'] = plan
    account_to_collect['advance_payment'] = advance_payment

    account_to_collect['debt_balance'] = debt_balance

    account_to_collect['current_payment'] = current_payment_number
    account_to_collect['payment'] = payment_amount
    account_to_collect['past_due_debt'] = past_due_debt
    account_to_collect['overdue_balance'] = overdue_balance

    accounts_to_collect.append(account_to_collect)

print(accounts_to_collect)
print(errors)

# crear excel de cobranzas
collections_filename = 'outputs/cuentas_a_cobrar_' + time.strftime("%Y%m%d-%H%M%S") + '.xlsx'
collections_excelwriter = exceladapter.ExcelWriter(collections_filename)
generated_sheet = collections_excelwriter.create_sheet('Cobranzas')

collections_builder = excelbuilder.BasicBuilder(generated_sheet, accounts_to_collect)

collections_builder.add_header("A", "Versión")
collections_builder.add_header("B", "Documento")
collections_builder.add_header("C", "Fecha de Vencimiento")

collections_builder.add_header("D", "Cliente")
collections_builder.add_header("E", "Ciudad")
collections_builder.add_header("F", "Dirección")

collections_builder.add_header("G", "Cuenta")
collections_builder.add_header("H", "Person")
collections_builder.add_header("I", "Orden de Compra")

collections_builder.add_header("J", "Última Cobranza")
collections_builder.add_header("K", "Valor de compra")
collections_builder.add_header("L", "Cuotas")
collections_builder.add_header("M", "Anticipo")

collections_builder.add_header("N", "Saldo Total")
collections_builder.add_header("O", "Cuota a pagar")
collections_builder.add_header("P", "Valor de cuota")
collections_builder.add_header("Q", "Saldo vencido")
collections_builder.add_header("R", "Deuda impaga a la fecha")

collections_builder.map_column("A", "version")
collections_builder.map_column("B", "document")
collections_builder.map_column("C", "due_date")
collections_builder.map_column("D", "customer")
collections_builder.map_column("E", "city")
collections_builder.map_column("F", "address")
collections_builder.map_column("G", "account")
collections_builder.map_column("H", "person")
collections_builder.map_column("I", "order")
collections_builder.map_column("J", "last_collection")
collections_builder.map_column("K", "total_purchase_value")
collections_builder.map_column("L", "plan")
collections_builder.map_column("M", "advance_payment")
collections_builder.map_column("N", "debt_balance")
collections_builder.map_column("O", "current_payment")
collections_builder.map_column("P", "payment")
collections_builder.map_column("Q", "past_due_debt")
collections_builder.map_column("R", "overdue_balance")

collections_builder.build()
collections_excelwriter.save()

## columnas

# valor total de compra
# saldo adeudado

# salen de la descripción
# Cuenta - OK
# Persona - OK
# Orden - OK

# Cuotas - OK

# Plan - OK
# Valor de cuota - importe si es histórico, surge de la descripción si es neuvo - OK
# Versión (Histórico - Nuevo) - OK

# fecha de último pago del cliente (viene de cobranzas) - QUE SEA DE LA ORDEN DE COMPRA - OK

# cuota acobrar (viene de cobranzas - última más uno)
# meses desde la venta (fórmula)

# de clientes:
# ciudad - OK
# teléfono - OK
# dirección - OK

# cuotas vencidas a hoy - OK
# monto vencido a hoy - OK
# saldo vencido - OK



# por ahora no
# saldo calculado
# cobranzas a la fecha para la OC


# GENERAR LISTADOS DE VALIDACIÓN
# todas las cobranzas sin descripción
