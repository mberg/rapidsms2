# coding=utf-8

import rapidsms
from models import Configuration, MessageLog, Record
from apps.simpleoperator.operators import *
from datetime import datetime
import re

def get_sim_balance(modem, carrier):
    operator_sentence   = modem.ussd(carrier.BALANCE_USSD)
    balance             = carrier.get_balance(operator_sentence)
    return balance

def get_topup_amount(modem, carrier, voucher):
    operator_topup      = carrier.build_topup_ussd(voucher)
    operator_sentence   = modem.ussd(operator_topup)
    amount              = carrier.get_amount_topup(operator_sentence)
    return amount

def import_function(func):
    s = func.rsplit(".", 1)
    x = __import__(s[0], fromlist=[s[0]])
    f = eval("x.%s" % s[1])
    return f

def add_record(sender, kind, value, text):
    record  = Record(sender=sender, kind=kind, value=value, text=text, date=datetime.now())
    return record.save()

def to_seconds(period):
    if period == 'hourly':
        return 3600
    elif period == 'daily':
        return 86400
    elif period == 'weekly':
        return 604800
    elif period == 'monthly':
        return 18144000
    elif period[0] == 's':
        return int(period[1:period.__len__()])
    elif period[0] == 'm':
        return int(period[1:period.__len__()]) * 60
    elif period[0] == 'h':
        return int(period[1:period.__len__()]) * 3600
    elif period[0] == 'd':
        return int(period[1:period.__len__()]) * 86400
    else:
        return 86400


class App (rapidsms.app.App):

    BALANCE_ID  = 'balance'
    TOPUP_ID    = 'topup'

    def start (self):
        self.config      = Configuration.get_dictionary()
        if self.config.__len__() < 1: raise Exception, "Need configuration fixture"
        for conf in self.config:
            try:
                x   = eval(self.config[conf])
                if x.__class__ == bool:
                    self.config[conf] = x
            except:
                pass
               
        # import carrier class from simpleoperator
        self.carrier    = eval("%s()" % self.config['carrier'])
        
        # storing backend for USSD interaction
        self.backend    = self._router.backends.pop()
        
        # set alias for logs
        self.me         = self.config['local_alias']
        
        self.keywords   = []
        self.keywords.append({'id': self.BALANCE_ID, 'keyw': self.config['keyword_balance']})
        self.keywords.append({'id': self.TOPUP_ID, 'keyw': self.config['keyword_topup']})
        
        # triggers initialization
        try:
            self.balance_allow  = import_function(self.config['balance_allow_helper'])
        except:
            self.balance_allow  = None
        try:
            self.balance_followup   = import_function(self.config['balance_followup'])
        except:
            self.balance_followup   = None
        try:
            self.topup_allow  = import_function(self.config['topup_allow_helper'])
        except:
            self.topup_allow  = None
        try:
            self.topup_followup   = import_function(self.config['topup_followup'])
        except:
            self.topup_followup   = None
        
        # Registering loops
        self.router.call_at(to_seconds(self.config['balance_check_interval']), self.period_balance_check)
        
        self.log    = self._router.log
        pass

    def parse (self, message):
        # Test if it's a prepaid message
        for keyword in self.keywords:
            if message.text.upper().startswith(keyword['keyw'].upper()):
                # message is prepaid
                message.PREPAID = True
                message.PREPAID_ACTION  = keyword['id']
                
                # log incoming message
                log     = MessageLog(sender=message.peer, recipient=self.me, text=message.text, date=datetime.now())
                log.save()
                
                return
        # message is not prepaid
        return False

    def handle (self, message):
        try:
            if not message.PREPAID: return False
        except AttributeError:
            return False
        
        self.log('info', "PREPAID handles message %s" % message.text)
        
        # Check SIM card Balance
        if message.PREPAID_ACTION == self.BALANCE_ID:
            
            # check authorization to call sim balance
            if self.config['balance_allow_everybody'] or (self.balance_allow and self.balance_allow(message=message, mobile=message.peer)):
                # get balance from simpleoperator
                balance = get_sim_balance(self.backend.modem, self.carrier)
                message.PREPAID_BALANCE = balance
                self.log('debug', "PREPAID BALANCE: %s" % balance)
                
                # record action
                add_record(sender=message.peer, kind='B', value=balance, text=message.text)
                
                # sends a very basic answer to emitter
                if self.config['balance_answer_request']:
                    message.respond("%(carrier)s balance: %(bal)s" % {'carrier': self.carrier, 'bal': balance})
                
                # triggers user's function
                if self.balance_followup:
                    self.log('debug', "PREPAID launches user's balance trigger")
                    return self.balance_followup(message=message, mobile=message.peer, balance=balance)

                # forward (or not) the message to pipe
                return self.config['balance_drop_successful']
            else:
                 # no permission, get off kid!
                pass
                
            return False
        
        elif message.PREPAID_ACTION == self.TOPUP_ID:
            # check authorization to call topup
            if self.config['balance_allow_everybody'] or (self.topup_allow and self.topup_allow(message=message, mobile=message.peer)):
                # process from simpleoperator
                try:
                    card_pin        = re.search('([0-9]+)', message.text).groups(0)[0]
                except:
                    message.PREPAID_TOPUP   = 0
                    return False
                
                self.log('debug', "Topup card # %s" % card_pin)
                amount              = get_topup_amount(self.backend.modem, self.carrier, card_pin)
                self.log('debug', "PREPAID TOPUP: %s" % amount)
                
                 # record action
                add_record(sender=message.peer, kind='T', value=amount, text=message.text)
                
                # sends a very basic answer to emitter
                if self.config['topup_answer_request']:
                    message.respond("%(carrier)s topup: %(am)s" % {'carrier': self.carrier, 'am': amount})
                
                # triggers user's function
                if self.topup_followup:
                    return self.topup_followup(message=message, mobile=message.peer, topup=amount)

                # forward (or not) the message to pipe
                return self.config['topup_drop_successful']
            else:
                 # no permission, get off kid!
                pass
                
            return False
        
        # fallback to forwarding message
        return False
        
    def period_balance_check(self):
        
        # check balance
        balance = get_sim_balance(self.backend.modem, self.carrier)
        
        # record action
        add_record(sender=self.me, kind='B', value=balance, text='period_balance_check')

        # alert someone if required
        if balance <= float(self.config['balance_alert_level']):
            content = "ALERT %(car)s balance is %(bal)s" % {'car': self.carrier, 'bal': balance}
            msg = self.backend.message(self.config['balance_alert_mobile'], content[:160])
            msg.PREPAID = True
            self.backend._router.outgoing(msg)
        
        return to_seconds(self.config['balance_check_interval'])

    def cleanup (self, message):
        """Perform any clean up after all handlers have run in the
           cleanup phase."""
        pass

    def outgoing (self, message):
        # log outgoing message
        try:
            if message.PREPAID:
                log     = MessageLog(sender=self.me, recipient=message.peer, text=message.text, date=datetime.now())
                log.save()
        except AttributeError:
            pass

    def stop (self):
        """Perform global app cleanup when the application is stopped."""
        pass
