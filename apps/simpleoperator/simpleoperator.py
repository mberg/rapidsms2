
import re

class SimpleOperator(object):

    CAPABILITIES    = {'USSD_BALANCE':False, 'USSD_TOPUP':False}
    BALANCE_USSD    = None
    TOPUP_USSD      = None
    TOPUP_USSD_FMT  = None

    def get_capabilities(self, feature="ALL"):
        if feature == "ALL":
            return self.CAPABILITIES
        else:
            return self.CAPABILITIES[feature]

    def get_balance(self, operator_string):
        return None
    
    def build_topup_ussd(self, card_pin):
        return None

    def get_amount_topup(self, operator_string):
        return None

    def __str__(self):
        return self.__class__.__name__

class UnparsableUSSDAnswer(Exception):
    pass
