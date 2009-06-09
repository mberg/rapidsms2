# coding=utf8

from models import Transaction
import simpleoperator
import rapidsms
import re
import unicodedata

def _(txt):
    return unicodedata.normalize('NFKD', txt).encode('ascii','ignore')

"""
    Orange Mali credit receiver App.
    Message: Vous avez recu 500F CFA du 73120896. Votre crédit est valable 15 jours.
    From: 7402
"""
class App (simpleoperator.SimpleOperatorApp):

    operator_numbers    = ['7402','585505']
    NUMBER_PREFIX       = '+223'

    def valid_message(self, message):

        operator_reg      = r'Vous avez recu ([0-9]{1,6})F CFA.*du (\+[0-9]{2,3})?([0-9]{8}).*?'
        res = re.findall(operator_reg, message.text)

        if res.__len__() > 0: # this is a credit message
            if res[0].__len__() in [2,3]: # valid message
                message.donnor  = self.NUMBER_PREFIX
                message.donnor +=   res[0][1] if (res[0].__len__() == 2) else (res[0][1] + res[0][2])
                message.amount  =   int(res[0][0])
                return True
            else:
                # malformed message. need to log
                pass
        else:
            return False

    def record_operation(self, message):
        transaction =   Transaction(mobile=message.donnor, amount=message.amount)
        transaction.save()
        message.transaction = transaction.id
        message.forward(message.donnor, _(u"Merci. Votre compte a ete credite de %(amount)sF (@%(id)s).") % {"amount":message.amount, "id":message.transaction})

        return False

