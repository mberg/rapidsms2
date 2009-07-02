# coding=utf-8

import rapidsms
from rapidsms.parsers.keyworder import Keyworder
from rapidsms.message import Message

from models import *
from utils import *
from ..simpleoperator.operators import *

import re
import unicodedata
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

#def _(txt): return txt #unicodedata.normalize('NFKD', ugettext(txt)).encode('ascii','ignore')

def authenticated (func):
    def wrapper (self, message, *args):
        if message.sender:
            return func(self, message, *args)
        else:
            send_message(self.backend, Member.system(), message.peer, _(u"You (%(number)s) are not allowed to perform this action. Join the network to be able to.") % {'number': message.peer}, 'err_unactive_user_notif', None, True, True)
            return True
    return wrapper

def registered (func):
    def wrapper (self, message, *args):
        if Member.objects.get(mobile=message.peer):
            return func(self, message, *args)
        else:
            send_message(self.backend, Member.system(), message.peer, _(u"You (%(number)s) are not a registered member of the Network. Contact a member to join.") % {'number': message.peer}, 'err_unknow_user_notif', None, True, True)
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

    def start (self):
        config      = Configuration.get_dictionary()
        if config.__len__() < 1: raise Exception, "Need configuration fixture"
        settings.LANGUAGE_CODE  = config["lang"]
        self.backend    = self._router.backends.pop()

    def parse (self, message):        
        member = Member.by_mobile(message.peer)
        if member:
            message.sender = member
        else:
            message.sender = None

    def handle (self, message):
        try:
            func, captures = self.keyword.match(self, message.text)
        except TypeError:
            # didn't find a matching function
            # send_message(self.backend, Member.system(), message.peer, _("Unknown or incorrectly formed command: %(msg)s... Please call 999-9999") % {"msg":message.text[:10]}, 'err_nomatch_notif', None, True, True)
            return False
        try:
            handled = func(self, message, *captures)
        except HandlerFailed, e:
            print e
            send_message(self.backend, Member.system(), message.peer, e, 'err_plain_notif', None, True, True)
            handled = True
        except Exception, e:
            print e
            send_message(self.backend, Member.system(), message.peer, _(u"An error has occured (%(e)s). Contact %(service_num)s. %(from)s") % {'service_num': config['service_num'], 'from':message.peer, 'e':e}, 'err_occured_notif', None, True, True)
            raise
        message.was_handled = bool(handled)
        if message.was_handled:
            log = MessageLog(sender=message.peer,recipient=Member.system().mobile,recipient_member=Member.system(),text=message.text[:140],date=datetime.datetime.now())
            if message.sender:
                log.sender_member   = message.sender
            log.save()
        return handled

    # Disable my account
    # stop
    @keyword(r'stop')
    @authenticated
    def stop_board (self, message):
        message.sender.active   = False
        message.sender.save()

        record_action('exit', message.sender, Member.system(), message.text, 0)

        self.followup_stop(message.sender)

        return True

    # Disable one's account
    # stop @bronx1
    @keyword(r'stop \@(\w+)')
    @sysadmin
    def stop_board (self, message, name):
        member    = Member.objects.get(alias=name)
        if not member.active: # already off
            send_message(self.backend, Member.system(), message.sender, _(u"%(member)s is not part of the network") % {'member':member.alias_display()}, 'board_was_off_notif', None, True, True)
            return True
        member.active   = False
        member.save()

        record_action('remote_exit', message.sender, member, message.text, 0)

        self.followup_stop(member)

        return True

    # message sending helper
    def followup_stop(self, sender):
        # we charge the manager if he has credit but don't prevent sending if he hasn't.
        if bool(config['send_exit_notif']):
            recipients  = Member.active_boards()
            send_message(self.backend, sender, recipients, _(u"Info: %(member)s has left the network.") % {'member':sender.alias_display()}, 'exit_notif_all', None, True, True)
        send_message(self.backend, Member.system(), sender, _(u"You have now left the network. Your balance, shall you come back, is %(credit)s. Good bye.") % {'credit':price_fmt(sender.credit)}, 'exit_notif_board', None, True, True)

    # Activate my disabled account
    # join
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

    # activate one's disabled account
    # join @bronx1
    @keyword(r'join \@(\w+)')
    @sysadmin
    def join_board (self, message, name):
        member    = Member.objects.get(alias=name)
        if member.active: # already on
            send_message(self.backend, Member.system(), message.sender, _(u"%(member)s is already active in the network") % {'member':member.alias_display()}, 'board_was_active_notif', None, True, True)
            return True
        member.active   = True
        member.save()

        record_action('remote_join', message.sender, member, message.text, 0)

        self.followup_join(member)

        return True

    # message sending helper
    def followup_join(self, sender):
        if bool(config['send_join_notif']):
            recipients  = Member.active_boards()
            try:
                recipients.remove(sender)
            except: pass

            try:
                send_message(self.backend, sender, recipients, _(u"Info: %(sender_zone)s has joined the network.") % {'sender_zone':sender.alias_display()}, 'join_notif_all', None, False, True)
            except InsufficientCredit:
                send_message(self.backend, Member.system(), sender, _(u"You just joined the network. Other boards hasn't been notified because your credit is insufficient (%(credit)s). Welcome!") % {'credit':price_fmt(sender.credit)}, 'silent_join_notif_board', None, True, True)
                return True
        
        send_message(self.backend, Member.system(), sender, _(u"Thank you for joining the network! We notified your peers of your return. Your balance is %(credit)s.") % {'credit':price_fmt(sender.credit)}, 'join_notif_board', None, True, True)

    # Add some credit to a member's account.
    # moneyup @bronx1 200
    @keyword(r'moneyup \@(\w+) ([0-9\.]+)')
    @sysadmin
    def moneyup_board (self, message, name, amount):
        member    = Member.objects.get(alias=name)
        member.credit   += float(amount)
        member.save()

        record_action('moneyup', message.sender, member, message.text, 0)

        send_message(self.backend, Member.system(), member, _(u"Thank you for toping-up your account. Your new balance is %(credit)s.") % {'credit':price_fmt(member.credit)}, 'moneyup_notif_board', None, True, True)

        return True

    # registers a member (usually Board) into the system.
    # register bronx1 567896 bronx
    @keyword(r'register \@?(\w+) (\+\d+) (\w+)( [\d\.]+)?( \d+)?( \w+)?')
    @sysadmin
    def register_board (self, message, alias, mobile, zonecode, credit, rating, membership):
        if credit == None: credit = 0
        if rating == None: rating = 1
        if membership == None: membership = 'board'

        credit  = float(credit)
        rating  = int(rating)
        zone        = Zone.by_name(zonecodes_from_string(zonecode).pop())
        membership  = MemberType.by_code(membership)

        if zone == None:
            return self.register_error(message.sender, 'Zone', zonecode)

        try:
            m       = Member.objects.get(mobile=mobile)
            return self.register_error(message.sender, 'Mobile', mobile)
        except: pass
        try:
            m       = Member.objects.get(alias=alias)
            return self.register_error(message.sender, 'Alias', alias)
        except: pass

        try:
            user    = User(username=alias)
            user.set_password(alias)
            user.save()
        except:
            return self.register_error(message.sender, 'Alias', alias)
        
        member      = Member(user=user, alias=alias, mobile=mobile,zone=zone, credit=float(credit), rating=int(rating), membership=membership, active=True)
        member.save()
        
        record_action('register', message.sender, member, message.text, 0)
        
        send_message(self.backend, Member.system(), message.sender, _(u"%(alias)s registration successful with %(mobile)s at %(zone)s. Credit is %(credit)s." % {'mobile': member.mobile, 'alias': member.alias_display(), 'credit':price_fmt(member.credit), 'zone':member.zone}), 'reg_ok_notif', None, True, True)
       
        self.followup_join(member)

        return True

    def register_error(self, peer, key, value):
        send_message(self.backend, Member.system(), peer, _(u"Unable to register. %(key)s (%(value)s) is either incorrect or in use by another member." % {'key': key, 'value': value}), 'mobile_exist_noreg_notif', None, True, True)
        return True

    # Add credit to account by sending voucher number
    # topup 5792109732680
    @keyword(r'topup (\d+)')
    @registered
    def topup_board (self, message, card_pin):

        return True # need to migrate to pygsm first
        operator            = eval("%s()" % operator_name)
        operator_topup      = operator.build_topup_ussd(card_pin)

        try:
            operator_sentence   = modem.ussd(operator_topup)
            amount              = operator.get_amount_topup(operator_sentence)
        except: raise Exception, operator_sentence

        message.sender.credit   += float(amount)
        message.sender.save()

        text    = u"%(op)s %(ussd)s: %(topup)s" % {'ussd': operator_topup, 'topup':price_fmt(amount), 'op':operator}
        record_action('topup', message.sender, Member.system(), text, 0)

        send_message(self.backend, Member.system(), message.sender, _(u"Thank you for toping-up your account. Your new balance is %(credit)s.") % {'credit':price_fmt(message.sender.credit)}, 'topup_notif_board', None, True, True)

        return True

    @keyword(r'ping')
    def ping (self, message):
        log = MessageLog(sender=message.peer,sender_member=None,recipient=Member.system().mobile,recipient_member=Member.system(),text=message.text,date=datetime.datetime.now())
        log.save()
        send_message(self.backend, Member.system(), message.peer, "pong")
        return True

    @keyword(r'help')
    @registered
    def help_board (self, message):
        message.sender  =   Member.objects.get(mobile=message.peer)

        if float(config['fair_price']) > message.sender.credit:
            # No Credit, No Help
            return True
        
        message.sender.credit   -= float(config['fair_price'])
        message.sender.save()

        record_action('help', message.sender, Member.system(), message.text, float(config['fair_price']))

        help_message    = _(u"Help: ad @target [+c] Your Text here | \
stop | \
join | \
topup voucher | \
help -- topup requires %s" % config['operator'])
        if message.sender.is_admin():
            help_message    = _("Admin Help: stop @name | \
join @name | \
register alias mobile zonecode[ credit rating membership] | \
moneyup @name amount")

        send_message(self.backend, Member.system(), message.sender, help_message, 'help_board', None, True, True)
        return True

    @keyword(r'balance\s?\@?([a-z0-9]*)')
    @registered
    def balance_board (self, message, target):
        message.sender  =   Member.objects.get(mobile=message.peer)
        if not target == None and target != "" and message.sender.is_admin():
            target  = Member.objects.get(alias=target)
        else:
            target  = message.sender

        if float(config['fair_price']) > message.sender.credit:
            # No Credit, No Balance
            return True
        
        message.sender.credit   -= float(config['fair_price'])
        message.sender.save()

        record_action('balance', message.sender, Member.system(), message.text, float(config['fair_price']))

        balance_message    = _(u"Balance for %(user)s: %(bal)s. Account is %(stat)s" % {'bal':price_fmt(target.credit), 'stat': target.status().lower(), 'user':target.alias_display()})
        if message.sender.is_admin():
            help_message    = _("Admin Help: stop @name amount")

        send_message(self.backend, Member.system(), message.sender, balance_message, 'balance_notif', None, True, True)
        return True

    @keyword(r'system\s?(\w*)')
    @sysadmin
    def system (self, message, command):

        if command == 'balance':
            operator            = eval("%s()" % config['operator'])

            operator_sentence   = self.backend.modem.ussd(operator.BALANCE_USSD)
            print operator_sentence
            balance             = operator.get_balance(operator_sentence)
            print balance

            request = _(u"%(ca)s %(rq)s> %(res)s") % {'ca': operator, 'rq': operator.BALANCE_USSD, 'res': operator_sentence}

            record_action('balance', message.sender, Member.system(), message.text, float(config['fair_price']))

            record_action('balance_check', message.sender, Member.system(), request, 0)
            
            balance_text= _(u"%(ca)s %(rq)s> %(res)s") % {'ca': operator, 'rq': operator.BALANCE_USSD, 'res': price_fmt(balance)}
            send_message(self.backend, Member.system(), message.sender, balance_text, 'balance_notif', None, True, True)
        
        return True
        

    # Place an ad on the system
    # sell @ny pictures of Paris Hilton Naked. +123456789
    @keyword(r'([a-z]+) ([a-z\,0-9\@]+) (.+)')
    @authenticated
    def new_announce (self, message, keyw, zonecode, text):
        print keyw
        targets     = zonecodes_from_string(zonecode.lower())
        recipients  = zone_recipients(targets, message.sender)
        adt         = AdType.by_code(keyw.lower())
        if adt == None:
            adt = AdType.by_code(config['dfl_ad_type'])
        print adt
        price       = message_cost(message.sender, recipients, adt)

        try:
            send_message(self.backend, message.sender, recipients, _(u"%(keyw)s: %(text)s") % {"text":text, 'sender':message.sender.alias_display(), 'keyw':adt.name}, 'ann_notif_all', adt)
            send_message(self.backend, Member.system(), message.sender, _(u"Thanks, your announce has been sent (%(price)s). Your balance is now %(credit)s.") % {'price':price_fmt(price), 'credit':price_fmt(message.sender.credit)}, 'ann_notif_board', None, True, True)
            record_action('ann', message.sender, Member.system(), message.text, 0, adt)
        except InsufficientCredit:
            send_message(self.backend, Member.system(), message.sender, _(u"Sorry, this message requires a %(price)s credit. You account balance is only %(credit)s. Top-up your account then retry.") % {'price':price_fmt(price), 'credit':price_fmt(message.sender.credit)}, 'ann_nonotif_board', None, True, True)

        return True


    def outgoing (self, message):
        # if info message ; down manager credit by 10F
        pass

