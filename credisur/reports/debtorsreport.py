

class DebtorsReport:
    
    def generate_report(self, accounts_to_collect, customers, first_day_of_last_month):

        result = self.build_result()

        for collection_account, accounts in accounts_to_collect.items():
            
            for acct in accounts:
                due_payments = acct['missing_payments']
                last_collection_date = acct['last_collection_as_date']            
                
                if not acct['version'] == "nuevo":
                    continue

                if self.is_debtor(due_payments, last_collection_date, first_day_of_last_month):

                    customer = self.get_account_customer(acct, customers)

                    debtor = self.build_debtor(acct, customer, collection_account)
                
                    result.append(debtor)

        return result


    def get_account_customer(self, acct, customers):
        return customers[acct['customer']]


    def is_debtor(self, due_payments, last_collection_date, first_day_of_last_month):
        if due_payments >= 3:
            return True
        
        if last_collection_date:
            return last_collection_date < first_day_of_last_month

        return False

    def build_result(self):
        return list()    


    def build_debtor(self, acct, customer, collection_account):
        # Ciudad	Cliente	Dirección	Teléfono	Fecha de Compra	Fecha de Vencimiento	
        # Orden de Compra	Última Cobranza	Cuotas	Cuotas a pagar	Valor de cuota	
        # Monto total a cobrar	Descripción	CBU

        debtor = {}
        debtor['city'] = customer['city']
        debtor['customer'] = acct['customer']
        debtor['address'] = customer['address']
        debtor['phone'] = customer['phone']
        debtor['date_of_purchase'] = acct['date_of_purchase']
        debtor['due_date'] = acct['due_date']
        debtor['order'] = acct['order']
        debtor['last_collection'] = acct['last_collection']        
        debtor['plan'] = acct['plan']
        debtor['missing_payments'] = acct['missing_payments']
        debtor['payment'] = acct['payment']
        debtor['amount_to_collect'] = acct['amount_to_collect']
        debtor['full_description'] = acct['full_description']
        debtor['cbu'] = customer['cbu']
        debtor['collection_account'] = collection_account

        return debtor