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

def logger(modem, message, type):
    if type in (1,2): print "%8s %s" % (type, message)
    pass

operator_name   = "MTNGhana"
operator    = eval("%s()" % operator_name)

modem = GsmModem(port="/dev/ttyUSB0", baudrate=115200, xonxoff=0, rtscts=1, logger=logger)
operator_sentence   = modem.ussd(operator.BALANCE_USSD)
#print operator_sentence
balance = operator.get_balance(operator_sentence)

message = u"%(op)s %(ussd)s: %(balance)s%(currency)s" % {'ussd': operator.BALANCE_USSD, 'balance':balance, 'op':operator, 'currency':config['currency']}
record_action('balance_check', Member.system(), Member.system(), message, 0)

print message

