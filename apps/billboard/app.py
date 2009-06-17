# coding=utf-8

import rapidsms
from rapidsms.parsers.keyworder import Keyworder
from rapidsms.message import Message

from ..orangeml.models import *
from models import *
from utils import *

import re
import unicodedata
from django.utils.translation import ugettext
from django.conf import settings

def _(txt): return unicodedata.normalize('NFKD', ugettext(txt)).encode('ascii','ignore')

def authenticated (func):
    def wrapper (self, message, *args):
        if message.sender:
            return func(self, message, *args)
        else:
            message.respond(_(u"You (%(number)s) are not allowed to perform this action. Join the network to be able to.") % {'number': message.peer})
            return True
            #return False
    return wrapper

def sysadmin (func):
    def wrapper (self, message, *args):
        if SysAdmin.granted(message.peer):
            return func(self, message, *args)
        else:
            return False
    return wrapper

class HandlerFailed (Exception):
    pass

class App (rapidsms.app.App):

    keyword = Keyworder()
    config  = {'price_per_board': 25, \
               'max_msg_len': 140, \
               'send_exit_notif': True, \
               'service_num': 000000, \
               'lang': 'en-us', \
               'currency': '$'}

    def start (self):
        self.config      = Configuration.get_dictionary()
        settings.LANGUAGE_CODE  = self.config["lang"]

    def parse (self, message):
        try:
            message.text    = unicodedata.normalize('NFKD', message.text.decode('ibm850')).encode('ascii','ignore')
        except Exception:
            pass
        
        manager = BoardManager.by_mobile(message.peer)
        if manager:
            message.sender = manager
        else:
            message.sender = None

    def handle (self, message):
        try: # message is credit from orangeml
            if message.transaction:
                transaction = Transaction.objects.get(id=message.transaction)
                manager     = BoardManager.by_mobile(transaction.mobile)
                manager.credit+= transaction.amount
                manager.save()
                transaction.delete()
                return True
        except AttributeError:
            pass

        try:
            func, captures = self.keyword.match(self, message.text)
        except TypeError:
            # didn't find a matching function
            # message.respond(_("Unknown or incorrectly formed command: %(msg)s... Please call 999-9999") % {"msg":message.text[:10]})
            return False
        try:
            handled = func(self, message, *captures)
        except HandlerFailed, e:
            message.respond(e.message)
            handled = True
        except Exception, e:
            message.respond(_(u"An error has occured. Please, contact %(service_num)s for more informations." % {'service_num': self.config['service_num']}))
            raise
        message.was_handled = bool(handled)
        return handled


    @keyword(r'new \@(\w+) (.+)')
    @authenticated
    def new_announce (self, message, zone, text):
        zone        = zone.lower()
        recipients  = recipients_from_zone(zone, message.peer)
        price       = price_for_msg(recipients, self.config['price_per_board'])
        if message.sender.credit >= price:
            self.group_send(message, recipients, _(u"Announce (@%(sender)s): %(text)s") % {"text":text, 'sender':message.sender.name})
            self.followup_new_announce(message, recipients)
        else:
            message.respond(_(u"Sorry, this message requires a %(price)d%(currency)s credit. You account balance is only %(credit)s%(currency)s. Top-up your account then retry.") % {'price':price, 'credit':message.sender.credit, 'currency': self.config['currency']})
        return True

    def followup_new_announce(self, message, recipients):
        price   = price_for_msg(recipients, self.config['price_per_board'])
        message.sender.credit    -= price
        message.sender.save()
        message.respond(_(u"Thanks, your announce has been sent (%(price)d%(currency)s). Your balance is now %(credit)s%(currency)s.") % {'price':price, 'credit':message.sender.credit, 'currency': self.config['currency']})

    @keyword(r'stop')
    @authenticated
    def stop_board (self, message):
        message.sender.active   = False
        message.sender.save()

        # we charge the manager if he has credit but don't prevent sending if he hasn't.
        if self.config['send_exit_notif']:
            recipients  = []
            all_active  = BoardManager.objects.filter(active=True)
            for board in all_active.iterator():
                recipients.append(board.mobile)
            self.group_send(message, recipients, _(u"Info: @%(sender)s has left the network.") % {'sender':message.sender.name})

        self.followup_stop_board(message, message.sender, recipients)
        return True

    def followup_stop_board(self, message, manager, recipients):
        price   = price_for_msg(recipients, self.config['price_per_board'])
        manager.credit     -= price
        if manager.credit < 0:
            manager.credit = 0
        manager.save()
        message.forward(manager.mobile, _(u"You have now left the network. Your balance, shall you come back, is %(credit)s%(currency)s. Good bye.") % {'credit':manager.credit, 'currency': self.config['currency']})

    @keyword(r'stop \@(\w+)')
    @sysadmin
    def stop_board (self, message, name):
        manager    = BoardManager.objects.get(name=name)
        if not manager.active: # already off
            message.respond(_(u"@%(manager)s is not part in the network") % {'manager':manager.name})
            return True
        manager.active   = False
        manager.save()

        # we charge the manager if he has credit but don't prevent sending if he hasn't.
        if self.config['send_exit_notif']:
            recipients  = []
            all_active  = BoardManager.objects.filter(active=True)
            for board in all_active.iterator():
                recipients.append(board.mobile)
            self.group_send(message, recipients, _(u"Info: @%(sender)s has left the network.") % {'sender':manager.name})

        self.followup_stop_board(message, manager, recipients.__len__())
        return True

    def group_send(self, message, recipients, text):
        for number in recipients:
            message.forward(number, text)
        pass

    def outgoing (self, message):
        # if info message ; down manager credit by 10F
        pass

