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

def authenticated (func):
    def wrapper (self, message, *args):
        if message.sender:
            return func(self, message, *args)
        else:
            send_message(backend=self.backend, sender=Member.system(), recipients=message.peer, content=_(u"You (%(number)s) are not allowed to perform this action. Join %(brand)s to be able to.") % {'brand': config['brand'], 'number': message.peer}, action='err_unactive_user_notif', overdraft=True, fair=True)
            return True
    return wrapper

def registered (func):
    def wrapper (self, message, *args):
        if Member.objects.get(mobile=message.peer):
            return func(self, message, *args)
        else:
            send_message(backend=self.backend, sender=Member.system(), recipients=message.peer, content=_(u"You (%(number)s) are not a registered member of %(brand)s. Contact a member to join.") % {'brand': config['brand'], 'number': message.peer}, action='err_unknow_user_notif', overdraft=True, fair=True)
            return True
    return wrapper

def sysadmin (func):
    def wrapper (self, message, *args):
        if message.sender and message.sender.is_admin():
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
        self.router.call_at(60, self.period_balance_check)

    def period_balance_check(self):
        try:
            operator            = eval("%s()" % config['operator'])
            operator_sentence   = self.backend.modem.ussd(operator.BALANCE_USSD)
            balance             = operator.get_balance(operator_sentence)
        except: return 999999

        system  = Member.system()

        request = _(u"%(carrier)s %(request)s> %(balance)s (%(response)s)") % {'carrier': operator, 'request': operator.BALANCE_USSD, 'balance': price_fmt(balance), 'response': operator_sentence}
        record_action('balance_check', system, system, request, 0)

        if balance <= float(config['balance_lowlevel']):
            balance -= send_message(backend=self.backend, sender=system, recipients=Member.objects.get(alias=config['balance_admin']), content=request, action='balance_notif', overdraft=True, fair=True)

        if balance != system.credit:
            old_credit  = system.credit
            diff    = (float(balance) - float(system.credit)).__abs__()
            system.credit  = balance
            system.save()
            record_action('adjust_credit', system, system, _("Credit was: %(old)s. Balance is: %(balance)s. Credit is: %(new)s.") % {'old': old_credit, 'balance': balance, 'new': system.credit}, diff)

        return to_seconds(config['check_balance_in'])

    def parse (self, message):        
        member = Member.by_mobile(message.peer)
        if member:
            message.sender = member
        else:
            message.sender = None

        log = MessageLog(sender=message.peer,sender_member=message.sender,recipient=Member.system().mobile,recipient_member=Member.system(),text=message.text,date=datetime.datetime.now())
        log.save()

    def handle (self, message):
        try:
            func, captures = self.keyword.match(self, message.text)
        except TypeError:
            # didn't find a matching function
            # send_message(backend=self.backend, sender=Member.system(), recipients=message.peer, content=_("Unknown or incorrectly formed command: %(msg)s...") % {"msg":message.text[:10]}, action='err_nomatch_notif', overdraft=True, fair=True)
            return False
        try:
            handled = func(self, message, *captures)
        except HandlerFailed, e:
            print e
            send_message(backend=self.backend, sender=Member.system(), recipients=message.peer, content=e, action='err_plain_notif', overdraft=True, fair=True)
            handled = True
        except Exception, e:
            print e
            send_message(backend=self.backend, sender=Member.system(), recipients=message.peer, content=_(u"An error has occured (%(e)s). Contact %(service_num)s. %(from)s") % {'service_num': config['service_num'], 'from':message.peer, 'e':e}, action='err_occured_notif', overdraft=True, fair=True)
            raise
        message.was_handled = bool(handled)
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
            send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=_(u"%(member)s is not part of %(brand)s.") % {'brand': config['brand'], 'member':member.alias_display()}, action='board_was_off_notif', overdraft=True, fair=True)
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
            send_message(backend=self.backend, sender=sender, recipients=recipients, content=_(u"Info: %(member)s has left %(brand)s.") % {'brand': config['brand'], 'member':sender.alias_display()}, action='exit_notif_all', overdraft=True, fair=True)
        send_message(backend=self.backend, sender=Member.system(), recipients=sender, content=_(u"You have now left %(brand)s. Your balance, if you come back, will be %(credit)s. Good bye.") % {'brand': config['brand'], 'credit':price_fmt(sender.credit)}, action='exit_notif_board', overdraft=True, fair=True)

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
            send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=_(u"%(member)s is already active in %(brand)s.") % {'brand': config['brand'], 'member':member.alias_display()}, action='board_was_active_notif', overdraft=True, fair=True)
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
                send_message(backend=self.backend, sender=sender, recipients=recipients, content=_(u"Info: %(sender_zone)s has joined %(brand)s.") % {'brand': config['brand'], 'sender_zone':sender.alias_display()}, action='join_notif_all', fair=True)
            except InsufficientCredit:
                send_message(backend=self.backend, sender=Member.system(), recipients=sender, content=_(u"Akwaaba! You just joined %(brand)s. Other boards haven't been notified because your credit is insufficient (%(credit)s).") % {'brand': config['brand'], 'credit':price_fmt(sender.credit)}, action='silent_join_notif_board', overdraft=True, fair=True)
                return True
        
        send_message(backend=self.backend, sender=Member.system(), recipients=sender, content=_(u"Thank you for re-joining %(brand)s! We notified your peers of your return. Your balance is %(credit)s.") % {'brand': config['brand'], 'credit':price_fmt(sender.credit)}, action='join_notif_board', overdraft=True, fair=True)

    # Add some credit to a member's account.
    # moneyup @bronx1 200
    @keyword(r'moneyup \@(\w+) ([0-9\.]+)')
    @sysadmin
    def moneyup_board (self, message, name, amount):
        member    = Member.objects.get(alias=name)
        member.credit   += float(amount)
        member.save()

        record_action('moneyup', message.sender, member, message.text, 0)

        send_message(backend=self.backend, sender=Member.system(), recipients=member, content=_(u"Thank you for topping-up your account. Your new balance is %(credit)s.") % {'credit':price_fmt(member.credit)}, action='moneyup_notif_board', overdraft=True, fair=True)

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
        
        member      = Member(user=user, alias=alias, name=alias, mobile=mobile,zone=zone, credit=float(credit), rating=int(rating), membership=membership, active=True)
        member.save()
        
        record_action('register', message.sender, member, message.text, 0)
        
        send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=_(u"%(alias)s registration successful with %(mobile)s at %(zone)s. Credit is %(credit)s." % {'mobile': member.mobile, 'alias': member.alias_display(), 'credit':price_fmt(member.credit), 'zone':member.zone}), action='reg_ok_notif', overdraft=True, fair=True)
       
        self.followup_join(member)

        return True

    def register_error(self, peer, key, value):
        send_message(backend=self.backend, sender=Member.system(), recipients=peer, content=_(u"Unable to register. %(key)s (%(value)s) is either incorrect or in use by another member." % {'key': key, 'value': value}), action='mobile_exist_noreg_notif', overdraft=True, fair=True)
        return True

    # Add credit to account by sending voucher number
    # topup 5792109732680
    @keyword(r'topup (\d+)')
    @registered
    def topup_board (self, message, card_pin):
        print card_pin
        operator            = eval("%s()" % config['operator'])
        print operator
        operator_topup      = operator.build_topup_ussd(card_pin)
        print operator_topup
        operator_sentence   = self.backend.modem.ussd(operator_topup)
        print operator_sentence
        amount              = operator.get_amount_topup(operator_sentence)
        print amount

        message.sender.credit   += float(amount)
        message.sender.save()

        text    = u"%(op)s %(ussd)s: %(topup)s" % {'ussd': operator_topup, 'topup':price_fmt(amount), 'op':operator}
        record_action('topup', message.sender, Member.system(), text, 0)

        send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=_(u"Thank you for topping-up your account. Your new balance is %(credit)s.") % {'credit':price_fmt(message.sender.credit)}, action='topup_notif_board', overdraft=True, fair=True)

        return True

    @keyword(r'ping')
    def ping (self, message):
        log = MessageLog(sender=message.peer,sender_member=None,recipient=Member.system().mobile,recipient_member=Member.system(),text=message.text,date=datetime.datetime.now())
        log.save()
        send_message(backend=self.backend, sender=Member.system(), recipients=message.peer, content="pong")
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

        help_message    = _(u"Help: code @target Your Text here | stop | join | topup {number} | balance | help -- topup requires %s" % config['operator'])
        if message.sender.is_admin():
            help_message    = _("Admin Help: stop @name | join @name | register alias mobile zonecode[ credit rating membership] | moneyup @name amount | balance[ @name]")

        send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=help_message, action='help_board', overdraft=True, fair=True)
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

        send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=balance_message, action='balance_notif', overdraft=True, fair=True)
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

            request = _(u"%(carrier)s %(request)s> %(balance)s (%(response)s)") % {'carrier': operator, 'request': operator.BALANCE_USSD, 'balance': price_fmt(balance), 'response': operator_sentence}

            record_action('balance', message.sender, Member.system(), message.text, float(config['fair_price']))

            record_action('balance_check', message.sender, Member.system(), request, 0)
            
            balance_text= _(u"%(carrier)s %(request)s> %(balance)s") % {'carrier': operator, 'request': operator.BALANCE_USSD, 'balance': price_fmt(balance)}
            send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=balance_text, action='balance_notif', overdraft=True, fair=True)
        
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
            send_message(backend=self.backend, sender=message.sender, recipients=recipients, content=_(u"%(keyw)s: %(text)s") % {"text":text, 'sender':message.sender.alias_display(), 'keyw':adt.name}, action='ann_notif_all', adt=adt)
            send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=_(u"Thanks, your announcement has been sent (%(price)s). Your balance is now %(credit)s.") % {'price':price_fmt(price), 'credit':price_fmt(message.sender.credit)}, action='ann_notif_board', overdraft=True, fair=True)
            record_action('ann', message.sender, Member.system(), message.text, 0, adt)
        except InsufficientCredit:
            send_message(backend=self.backend, sender=Member.system(), recipients=message.sender, content=_(u"Sorry, this message requires a %(price)s credit. You account balance is only %(credit)s. Top-up your account then retry.") % {'price':price_fmt(price), 'credit':price_fmt(message.sender.credit)}, action='ann_nonotif_board', overdraft=True, fair=True)

        return True


    def outgoing (self, message):
        # if info message ; down manager credit by 10F
        pass

