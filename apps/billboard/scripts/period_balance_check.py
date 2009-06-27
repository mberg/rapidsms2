#!/usr/bin/env python

import sys
import os
path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__))))
path = os.path.dirname(os.path.dirname(os.path.dirname(path)))
os.chdir(path)
sys.path.append(path)

os.environ['RAPIDSMS_INI'] = os.path.join(path, "rapidsms.ini")
os.environ['DJANGO_SETTINGS_MODULE'] = 'rapidsms.webui.settings'

import rapidsms
from rapidsms import *
from apps.billboard.models import *
from apps.billboard.utils import *
from datetime import *
from apps.simpleoperator.operators import *
from pygsm import * # requires pygsm fork with ussd method!
import time
from rapidsms.config import Config
conf = Config("rapidsms.ini")

def logger(modem, message, type):
    if type in (1,2): print "%8s %s" % (type, message)
    pass

operator_name   = config['operator']
operator    = eval("%s()" % operator_name)

modem = GsmModem(port=conf["modem"]["port"], baudrate=conf["modem"]["baudrate"], xonxoff=conf["modem"]["xonxoff"], rtscts=conf["modem"]["rtscts"], logger=logger)
operator_sentence   = modem.ussd(operator.BALANCE_USSD)
#print operator_sentence
balance = operator.get_balance(operator_sentence)

message = u"%(op)s %(ussd)s: %(balance)s" % {'ussd': operator.BALANCE_USSD, 'balance':price_fmt(balance), 'op':operator}
record_action('balance_check', Member.system(), Member.system(), message, 0)

print message

