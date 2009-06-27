
from simpleoperator import *

## GHANA
class MTNGhana(SimpleOperator):
    
    CAPABILITIES    = {'USSD_BALANCE':True, 'USSD_TOPUP':True}
    BALANCE_USSD    = "*124#"
    TOPUP_USSD      = "*125*"
    TOPUP_USSD_FMT  = "%s%s#"

    def get_balance(self, operator_string):
        balance_grp = re.search('Your Balance is ([0-9\.]+) Ghana Cedi\(s\)', operator_string)
        try:
            return float(balance_grp.groups()[0])
        except:
            raise UnparsableUSSDAnswer, operator_string
    
    def build_topup_ussd(self, card_pin):
        return self.TOPUP_USSD_FMT % (self.TOPUP_USSD, card_pin)

    def get_amount_topup(self, operator_string):
        return None

class TigoGhana(SimpleOperator):
    
    CAPABILITIES    = {'USSD_BALANCE':True, 'USSD_TOPUP':True}
    BALANCE_USSD    = "*124#"
    TOPUP_USSD      = "*125*"
    TOPUP_USSD_FMT  = "%s%s#"

    def get_balance(self, operator_string):
        balance_grp = re.search('Your Balance is ([0-9\.]+) Ghana Cedi\(s\)', operator_string)
        try:
            return float(balance_grp.groups()[0])
        except:
            raise UnparsableUSSDAnswer, operator_string
    
    def build_topup_ussd(self, card_pin):
        return self.TOPUP_USSD_FMT % (self.TOPUP_USSD, card_pin)

    def get_amount_topup(self, operator_string):
        return None

## MALI
class OrangeMali(SimpleOperator):
    
    CAPABILITIES    = {'USSD_BALANCE':True, 'USSD_TOPUP':True}
    BALANCE_USSD    = "#123#"
    TOPUP_USSD      = "*123*"
    TOPUP_USSD_FMT  = "%s%s#"

    def get_balance(self, operator_string):
        return None
    
    def build_topup_ussd(self, card_pin):
        return None

    def get_amount_topup(self, operator_string):
        return None

class Malitel(SimpleOperator):
    
    CAPABILITIES    = {'USSD_BALANCE':True, 'USSD_TOPUP':True}
    BALANCE_USSD    = "#122#"
    TOPUP_USSD      = "*111*"
    TOPUP_USSD_FMT  = "%s%s#"

    def get_balance(self, operator_string):
        return None
    
    def build_topup_ussd(self, card_pin):
        return None

    def get_amount_topup(self, operator_string):
        return None

## SENEGAL
class OrangeSenegal(SimpleOperator):
    
    CAPABILITIES    = {'USSD_BALANCE':True, 'USSD_TOPUP':True}
    BALANCE_USSD    = "#123#"
    TOPUP_USSD      = "*123*"
    TOPUP_USSD_FMT  = "%s%s#"

    def get_balance(self, operator_string):
        return None
    
    def build_topup_ussd(self, card_pin):
        return None

    def get_amount_topup(self, operator_string):
        return None

