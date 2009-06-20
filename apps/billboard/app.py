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
            send_message(Member.system(), message.peer, _(u"You (%(number)s) are not allowed to perform this action. Join the network to be able to.") % {'number': message.peer}, True)
            return True
    return wrapper

def registered (func):
    def wrapper (self, message, *args):
        if Member.objects.get(mobile=message.peer):
            return func(self, message, *args)
        else:
            send_message(Member.system(), message.peer, _(u"You (%(number)s) are not a registered member of the Network. Contact a member to join.") % {'number': message.peer}, True)
            return True
    return wrapper

def sysadmin (func):
    def wrapper (self, message, *args):
        if message.sender.is_admin():
            return func(self, message, *args)
        else:
            return False
    return wrapper

class HandlerFailed (Exception):
    pass

class App (rapidsms.app.App):

    keyword = Keyworder()
    config  = {'price_per_board': 25, 'max_msg_len': 140, 'send_exit_notif': True, 'send_join_notif': True, 'service_num': 000000, 'lang': 'en-us', 'currency': '$'}

    def start (self):
        self.config      = Configuration.get_dictionary()
        settings.LANGUAGE_CODE  = self.config["lang"]

    def parse (self, message):
        try:
            message.text    = unicodedata.normalize('NFKD', message.text.decode('ibm850')).encode('ascii','ignore')
        except Exception:
            pass
        
        member = Member.by_mobile(message.peer)
        if member:
            message.sender = member
        else:
            message.sender = None

    def handle (self, message):
        try: # message is credit from orangeml
            if message.transaction:
                transaction = Transaction.objects.get(id=message.transaction)
                member     = Member.by_mobile(transaction.mobile)
                member.credit+= transaction.amount
                member.save()
                transaction.delete()
                return True
        except AttributeError:
            pass

        try:
            func, captures = self.keyword.match(self, message.text)
        except TypeError:
            # didn't find a matching function
            # send_message(Member.system(), message.peer, _("Unknown or incorrectly formed command: %(msg)s... Please call 999-9999") % {"msg":message.text[:10]}, True)
            return False
        try:
            handled = func(self, message, *captures)
        except HandlerFailed, e:
            send_message(Member.system(), message.peer, e.message, True)
            handled = True
        except Exception, e:
            send_message(Member.system(), message.peer, _(u"An error has occured. Please, contact %(service_num)s for more informations.") % {'service_num': self.config['service_num']}, True)
            raise
        message.was_handled = bool(handled)
        if message.was_handled:
            log = MessageLog(sender=message.peer,recipient=Member.system().mobile,recipient_member=Member.system(),text=message.text[:140],date=datetime.datetime.now())
            if message.sender:
                log.sender_member   = message.sender
            log.save()
        return handled


    @keyword(r'new \@(\w+) (.+)')
    @authenticated
    def new_announce (self, message, zone, text):
        zone        = zone.lower()
        recipients  = zone_recipients(zone, message.sender)
        price       = message_cost(message.sender, recipients)
        try:
            send_message(message.sender, recipients, _(u"Announce (@%(sender)s): %(text)s") % {"text":text, 'sender':message.sender.name})
        except InsufficientCredit:
            send_message(Member.system(), message.sender, _(u"Sorry, this message requires a %(price)d%(currency)s credit. You account balance is only %(credit)s%(currency)s. Top-up your account then retry.") % {'price':price, 'credit':message.sender.credit, 'currency': self.config['currency']}, True)

        send_message(Member.system(), message.sender, _(u"Thanks, your announce has been sent (%(price)d%(currency)s). Your balance is now %(credit)s%(currency)s.") % {'price':price, 'credit':message.sender.credit, 'currency': self.config['currency']}, True)
        return True

    @keyword(r'stop')
    @authenticated
    def stop_board (self, message):
        message.sender.active   = False
        message.sender.save()

        # we charge the manager if he has credit but don't prevent sending if he hasn't.
        if self.config['send_exit_notif']:
            recipients  = Member.active_boards()
            send_message(message.sender, recipients, _(u"Info: @%(sender)s has left the network.") % {'sender':message.sender.alias}, True)
        send_message(Member.system(), message.sender, _(u"You have now left the network. Your balance, shall you come back, is %(credit)s%(currency)s. Good bye.") % {'credit':message.sender.credit, 'currency': self.config['currency']}, True)
        
        return True

    @keyword(r'stop \@(\w+)')
    @sysadmin
    def stop_board (self, message, name):
        member    = Member.objects.get(alias=name)
        if not member.active: # already off
            send_message(Member.system(), message.sender, _(u"@%(member)s is not part in the network") % {'member':member.alias}, True)
            return True
        member.active   = False
        member.save()

        # we charge the manager if he has credit but don't prevent sending if he hasn't.
        if self.config['send_exit_notif']:
            recipients  = Member.active_boards()
            send_message(member, recipients, _(u"Info: @%(member)s has left the network.") % {'member':member.alias}, True)
        send_message(Member.system(), member, _(u"You have now left the network. Your balance, shall you come back, is %(credit)s%(currency)s. Good bye.") % {'credit':member.credit, 'currency': self.config['currency']}, True)
        return True

    @keyword(r'join')
    @registered
    def join_board (self, message):
        message.sender  =   Member.objects.get(mobile=message.peer)
        if message.sender.active:
            return True
        message.sender.active   = True
        message.sender.save()

        if self.config['send_join_notif']:
            recipients  = Member.active_boards()
            recipients.remove(message.sender)
            try:
                send_message(message.sender, recipients, _(u"Info: %(sender_zone)s has joined the network.") % {'sender_zone':message.sender.alias})
            except InsufficientCredit:
                send_message(Member.system(), message.sender, _(u"You just joined the network. Other boards hasn't been notified because your credit is insufficient (%(credit)s%(currency)s). Welcome back!") % {'credit':message.sender.credit, 'currency': self.config['currency']}, True)
                return True
        send_message(Member.system(), message.sender, _(u"Thank you for joining back the network! We notified your peers of your return. Your balance is %(credit)s%(currency)s.") % {'credit':message.sender.credit, 'currency': self.config['currency']}, True)
        return True

    @keyword(r'join \@(\w+)')
    @sysadmin
    def join_board (self, message, name):
        member    = Member.objects.get(alias=name)
        if member.active: # already on
            send_message(Member.system(), message.sender, _(u"@%(member)s is already active in the network") % {'member':member.alias}, True)
            return True
        member.active   = True
        member.save()

        if self.config['send_join_notif']:
            recipients  = Member.active_boards()
            recipients.remove(member)
            try:
                send_message(member, recipients, _(u"Info: %(sender_zone)s has joined the network.") % {'sender_zone':member.alias})
            except InsufficientCredit:
                send_message(Member.system(), member, _(u"You just joined the network. Other boards hasn't been notified because your credit is insufficient (%(credit)s%(currency)s). Welcome back!") % {'credit':member.credit, 'currency': self.config['currency']}, True)
                return True
        send_message(Member.system(), member, _(u"Thank you for joining back the network! We notified your peers of your return. Your balance is %(credit)s%(currency)s.") % {'credit':member.credit, 'currency': self.config['currency']}, True)
        return True

    def outgoing (self, message):
        # if info message ; down manager credit by 10F
        pass

