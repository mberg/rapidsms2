
from simpleoperator import *

## GHANA
class MTNGhana(SimpleOperator):
    
    CAPABILITIES    = {'USSD_BALANCE':True, 'USSD_TOPUP':True}
    BALANCE_USSD    = "*124#"
    TOPUP_USSD      = "*125*"
    TOPUP_USSD_FMT  = "%s%s#"

    def get_balance(self, operator_string):
        #Your Balance is 5.84 Ghana Cedi(s),and your bonus account is 0.00.Simply keep your line active before Sep 25 2009 to keep your number forever.
        balance_grp = re.search('Your Balance is ([0-9\.]+) Ghana Cedi\(s\)', operator_string)
        try:
            return float(balance_grp.groups()[0])
        except:
            raise UnparsableUSSDAnswer, operator_string
    
    def build_topup_ussd(self, card_pin):
        return self.TOPUP_USSD_FMT % (self.TOPUP_USSD, card_pin)

    def get_amount_topup(self, operator_string):
        #You have recharged 5.50 GHC.New Balance is 5.84 GHC remember to start with 024 or 054 when you call an MTN number.Enjoy 40% discount with MTN Family&Friends
        amount_grp  = re.search('You have recharged ([0-9\.]+)', operator_string)
        try:
            return float(amount_grp.groups()[0])
        except:
            raise UnparsableUSSDAnswer, operator_string

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

