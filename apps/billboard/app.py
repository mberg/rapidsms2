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
            send_message(Member.system(), message.peer, _(u"You (%(number)s) are not allowed to perform this action. Join the network to be able to.") % {'number': message.peer}, 'err_unactive_user_notif', True)
            return True
    return wrapper

def registered (func):
    def wrapper (self, message, *args):
        if Member.objects.get(mobile=message.peer):
            return func(self, message, *args)
        else:
            send_message(Member.system(), message.peer, _(u"You (%(number)s) are not a registered member of the Network. Contact a member to join.") % {'number': message.peer}, 'err_unknow_user_notif', True)
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
        config      = Configuration.get_dictionary()
        settings.LANGUAGE_CODE  = config["lang"]

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
            # send_message(Member.system(), message.peer, _("Unknown or incorrectly formed command: %(msg)s... Please call 999-9999") % {"msg":message.text[:10]}, 'err_nomatch_notif', True)
            return False
        try:
            handled = func(self, message, *captures)
        except HandlerFailed, e:
            send_message(Member.system(), message.peer, e.message, 'err_plain_notif', True)
            handled = True
        except Exception, e:
            send_message(Member.system(), message.peer, _(u"An error has occured (%(e)s). Contact %(service_num)s. %(from)s") % {'service_num': config['service_num'], 'from':message.peer, 'e':e}, 'err_occured_notif', True)
            raise
        message.was_handled = bool(handled)
        if message.was_handled:
            log = MessageLog(sender=message.peer,recipient=Member.system().mobile,recipient_member=Member.system(),text=message.text[:140],date=datetime.datetime.now())
            if message.sender:
                log.sender_member   = message.sender
            log.save()
        return handled

    @keyword(r'new ([a-z\,0-9\@]+) (.+)')
    @authenticated
    def new_announce (self, message, zonecode, text):
        targets     = zonecodes_from_string(zonecode.lower())
        recipients  = zone_recipients(targets, message.sender)
        price       = message_cost(message.sender, recipients)
        try:
            # over simplified for know ; not sure how we'll use tags
            tags    = re.search('^\s?\+([a-z])', text).groups()[0]
        except:
            tags    = []

        try:
            send_message(message.sender, recipients, _(u"Announce (%(sender)s): %(text)s") % {"text":text, 'sender':message.sender.alias_display()}, 'ann_notif_all')
        except InsufficientCredit:
            send_message(Member.system(), message.sender, _(u"Sorry, this message requires a %(price)s%(currency)s credit. You account balance is only %(credit)s%(currency)s. Top-up your account then retry.") % {'price':price, 'credit':message.sender.credit, 'currency': config['currency']}, 'ann_nonotif_board', True)

        record_action('ann', message.sender, Member.system(), message.text, 0, tags)

        send_message(Member.system(), message.sender, _(u"Thanks, your announce has been sent (%(price)s%(currency)s). Your balance is now %(credit)s%(currency)s.") % {'price':price, 'credit':message.sender.credit, 'currency': config['currency']}, 'ann_notif_board', True)
        return True

    @keyword(r'stop')
    @authenticated
    def stop_board (self, message):
        message.sender.active   = False
        message.sender.save()

        record_action('exit', message.sender, Member.system(), message.text, 0)

        self.followup_stop(message.sender)

        return True

    @keyword(r'stop \@(\w+)')
    @sysadmin
    def stop_board (self, message, name):
        member    = Member.objects.get(alias=name)
        if not member.active: # already off
            send_message(Member.system(), message.sender, _(u"%(member)s is not part of the network") % {'member':member.alias_display()}, 'board_was_off_notif', True)
            return True
        member.active   = False
        member.save()

        record_action('remote_exit', message.sender, member, message.text, 0)

        self.followup_stop(member)

        return True

    def followup_stop(self, sender):
        # we charge the manager if he has credit but don't prevent sending if he hasn't.
        if config['send_exit_notif']:
            recipients  = Member.active_boards()
            send_message(sender, recipients, _(u"Info: %(member)s has left the network.") % {'member':sender.alias_display()}, 'exit_notif_all', True)
        send_message(Member.system(), sender, _(u"You have now left the network. Your balance, shall you come back, is %(credit)s%(currency)s. Good bye.") % {'credit':sender.credit, 'currency': config['currency']}, 'exit_notif_board', True)

    @keyword(r'join')
    @registered
    def join_board (self, message):
        message.sender  =   Member.objects.get(mobile=message.peer)
        if message.sender.active:
            return True
        message.sender.active   = True
        message.sender.save()

        record_action('join', message.sender, Member.system(), message.text, 0)

        self.followup_join(message.sender)

        return True

    @keyword(r'join \@(\w+)')
    @sysadmin
    def join_board (self, message, name):
        member    = Member.objects.get(alias=name)
        if member.active: # already on
            send_message(Member.system(), message.sender, _(u"%(member)s is already active in the network") % {'member':member.alias_display()}, 'board_was_active_notif', True)
            return True
        member.active   = True
        member.save()

        record_action('remote_join', message.sender, member, message.text, 0)

        self.followup_join(member)

        return True

    def followup_join(self, sender):
        if config['send_join_notif']:
            recipients  = Member.active_boards()
            recipients.remove(sender)
            try:
                send_message(sender, recipients, _(u"Info: %(sender_zone)s has joined the network.") % {'sender_zone':sender.alias_display()}, 'join_notif_all')
            except InsufficientCredit:
                send_message(Member.system(), sender, _(u"You just joined the network. Other boards hasn't been notified because your credit is insufficient (%(credit)s%(currency)s). Welcome back!") % {'credit':sender.credit, 'currency': config['currency']}, 'silent_join_notif_board', True)
                return True
        
        send_message(Member.system(), sender, _(u"Thank you for joining back the network! We notified your peers of your return. Your balance is %(credit)s%(currency)s.") % {'credit':sender.credit, 'currency': config['currency']}, 'join_notif_board', True)

    @keyword(r'moneyup \@(\w+) ([0-9\.]+)')
    @sysadmin
    def join_board (self, message, name, amount):
        member    = Member.objects.get(alias=name)
        member.credit   += float(amount)

        record_action('moneyup', message.sender, member, message.text, 0)

        send_message(Member.system(), member, _(u"Thank you for toping-up your account. Your new balance is %(credit)s%(currency)s.") % {'credit':member.credit, 'currency': config['currency']}, 'moneyup_notif_board', True)

        return True


    def outgoing (self, message):
        # if info message ; down manager credit by 10F
        pass

