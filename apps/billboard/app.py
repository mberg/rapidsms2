# coding=utf8

import rapidsms
from rapidsms.parsers.keyworder import Keyworder
from rapidsms.message import Message

from ..orangeml.models import *
from models import *

import re
import unicodedata

def _(txt): return unicodedata.normalize('NFKD', txt).encode('ascii','ignore')

def authenticated (func):
    def wrapper (self, message, *args):
        if message.sender:
            return func(self, message, *args)
        else:
            message.respond(_(u"%s ne fait pas partie du réseau.") % message.peer)
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

def recurs_zones(zone):
    zonelist    = []
    all_zones   = Zone.objects.filter(zone=zone)
    for azone in all_zones.iterator():
        zonelist += recurs_zones(azone)
        zonelist.append(azone)
    return zonelist

class App (rapidsms.app.App):

    keyword = Keyworder()
    config  = {'price_per_board': 25, \
               'max_msg_len': 140, \
               'send_exit_notif': True}

    def start (self):
        self.config      = Configuration.get_dictionary()
        pass

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
            message.respond(_(u"Une erreur s'est produite. Contactez le 73120896."))
            raise
        message.was_handled = bool(handled)
        return handled


    @keyword(r'new \@(\w+) (.+)')
    @authenticated
    def new_announce (self, message, zone, text):
        zone        = zone.lower()
        recipients  = self.recipients_from_zone(zone, message.peer)        
        self.group_send(message, recipients, _(u"Annonce (@%(sender)s): %(text)s") % {"text":text, 'sender':message.sender.name})
        self.followup_new_announce(message, recipients)
        return True

    def followup_new_announce(self, message, recipients):
        price   = self.price_for_msg(recipients)
        message.sender.credit    -= price
        message.sender.save()
        message.respond(_(u"Merci, votre annonce a été envoyée (%(price)dF). Il vous reste %(credit)sF de crédit.") % {'price':price, 'credit':message.sender.credit})

    def price_for_msg(self, message, recipients):
        bulk    = self.config['price_per_board']
        price   = 0
        for recip in recipients:
            bm      = BoardManager.by_mobile(recip)
            price   += (bm.cost * bulk)
        return price

    @keyword(r'stop')
    @authenticated
    def stop_board (self, message):
        message.sender.active   = False
        message.sender.save()

        if self.config['send_exit_notif']:
            recipients  = []
            all_active  = BoardManager.objects.filter(active=True)
            for board in all_active.iterator():
                recipients.append(board.mobile)
            self.group_send(message, recipients, _(u"Info: @%(sender)s a quitté le réseau.") % {'sender':message.sender.name})

        self.followup_stop_board(message, message.sender, recipients)
        return True

    def followup_stop_board(self, message, manager, recipients):
        price   = self.price_for_msg(recipients)
        manager.credit     -= price
        if manager.credit < 0:
            manager.credit = 0
        manager.save()
        message.forward(manager.mobile, _(u"Vous avez quitté le réseau. Votre crédit (si vous souhaitez revenir) est de %(credit)sF. Au revoir.") % {'credit':manager.credit})

    @keyword(r'stop \@(\w+)')
    @sysadmin
    def stop_board (self, message, name):
        manager    = BoardManager.objects.get(name=name)
        if not manager.active: # already off
            message.respond(_(u"@%(manager)s ne fait pas partie du réseau.") % {'manager':manager.name})
            return True
        manager.active   = False
        manager.save()

        if self.config['send_exit_notif']:
            recipients  = []
            all_active  = BoardManager.objects.filter(active=True)
            for board in all_active.iterator():
                recipients.append(board.mobile)
            self.group_send(message, recipients, _(u"Info: @%(sender)s a quitté le réseau.") % {'sender':manager.name})

        self.followup_stop_board(message, manager, recipients.__len__())
        return True

    def group_send(self, message, recipients, text):
        for number in recipients:
            message.forward(number, text)
        pass

    def recipients_from_zone(self, zone, exclude=None):     
        recipients  = []
        query_zone  = Zone.objects.get(name=zone)
        all_zones   = recurs_zones(query_zone)
        all_boards  = BoardManager.objects.filter(zone__in=all_zones)

        for board in all_boards.iterator():
            recipients.append(board.mobile)

        if not exclude == None:
            recipients.remove(exclude)

        return recipients

    def outgoing (self, message):
        # if info message ; down manager credit by 10F
        pass

