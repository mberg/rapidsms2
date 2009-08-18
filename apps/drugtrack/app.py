# coding=utf-8

import rapidsms
from apps.tinystock.logic import *
from apps.tinystock.exceptions import *
from models import Zone, Facility, Provider, User
from apps.tinystock.models import StoreProvider, KindOfItem, Item, StockItem
from django.utils.translation import ugettext as _
from rapidsms.parsers.keyworder import Keyworder
from utils import *
from datetime import datetime

class HandlerFailed (Exception):
    pass

class MalformedRequest (Exception):
    pass

def registered (func):
    def wrapper (self, message, *args):
        if Provider.by_mobile(message.peer):
            return func(self, message, *args)
        else:
            message.respond(_(u"Sorry, only registered users can access this program."))
            return True
    return wrapper

def admin (func):
    def wrapper (self, message, *args):
        x = Provider.by_mobile(message.peer)
        if x and x.admin:
            return func(self, message, *args)
        else:
            message.respond(_(u"Sorry, only administrators of the system can perform this action."))
            return False
    return wrapper

class App (rapidsms.app.App):

    keyword     = Keyworder()
    # debug! shouldn't exist. sets the char to identify drugs
    # in sms. used because httptester doesn'h handles #. use $ instead
    drug_code   = '#'

    def start (self):
        self.backend    = self._router.backends.pop()

    def parse (self, message):
        """Parse and annotate messages in the parse phase."""
        pass

    def handle (self, message):
        try:
            func, captures = self.keyword.match(self, message.text)
        except TypeError:
            # didn't find a matching function
            return False
        try:
            handled = func(self, message, *captures)
        except HandlerFailed, e:
            print e
            send_message(backend=self.backend, sender=Member.system(), receivers=message.peer, content=e, action='err_plain_notif', overdraft=True, fair=True)
            handled = True
        except Exception, e:
            print e
            message.respond(_(u"An error has occured (%(e)s).") % {'e': e})
            raise
        message.was_handled = bool(handled)
        return handled

    @keyword(r'join (\w+) (\w+) (\w+) (\w+) (\w+) ([0-9\+]+)')
    @admin
    def register_provider (self, message, role, password, last, first, alias, mobile):
        ''' Adds people into the system 
            JOIN CHW PASSWORD LAST FIRST ALIAS'''
        
        # If error in role, assume CHW
        role    = role.upper()
        if role == 'PHA':
            role    = Provider.PHA_ROLE
        else:
            role    = Provider.CHW_ROLE

        # retrieve clinic
        clinic      = Facility.by_alias(password)
        
        # PHA _must_ be affiliated to a Clinic
        if role == Provider.PHA_ROLE and clinic == None:
            message.respond(_(u"Registration Failed. PHA needs correct clinic ID. '%(input)s' is not.") % {'input': password})
            return True

        # Verify alias availability
        dumb    = Provider.by_alias(alias)
        if not dumb == None:
            message.respond(_(u"Registration Failed. Alias already in use by %(prov)s") % {'prov': dumb.display_full()})
            return True

        # Verify mobile slot
        dumb    = Provider.by_mobile(mobile)
        if not dumb == None:
            message.respond(_(u"Registration Failed. mobile number already in use by %(prov)s") % {'prov': dumb.display_full()})
            return True
        
        # Create provier
        provider    = Provider(alias=alias, first_name=first, last_name=last, role=role, active=True, clinic=clinic, mobile=mobile)
        provider.save()

        # send notifications
        message.respond(_(u"SUCCESS. %(prov)s has been registered with alias %(al)s.") % {'prov': provider.display_full(), 'al': provider.alias})
        
        if not provider.mobile == None:
            message.forward(provider.mobile, _(u"Welcome %(prov)s. You have been registered with alias %(al)s.") % {'prov': provider.display_full(), 'al': provider.alias})
    
        return True

    def do_transfer_drug(self, message, sender, receiver, item, quantity):
        
        #try:
        log = transfer_item(sender=sender, receiver=receiver, item=item, quantity=int(quantity))
        '''except ItemNotInStore:
            message.respond(_(u"Distribution request failed. You do not have %(med)s") % {'med': item})
            return True
        except NotEnoughItemInStock:
            message.respond(_(u"Distribution request failed. You can't transfer %(q)s %(it)s to %(rec)s because you only have %(stk)s.") % {'q': quantity, 'it': item.name, 'rec': receiver.display_full(), 'stk': StockItem.objects.get(peer=sender, item=item).quantity})
            return True
        '''

        message.forward(receiver.mobile, "CONFIRMATION #%(d)s-%(sid)s-%(rid)s-%(lid)s You have received %(quantity)s %(item)s from %(sender)s. If not correct please reply: CANCEL %(lid)s" % {
            'quantity': quantity,
            'item': item.name,
            'sender': sender.display_full(),
            'd': log.date.strftime("%d%m%y"),
            'sid': sender.id,
            'rid': receiver.id,
            'lid': log.id
        })

        message.respond("CONFIRMATION #%(d)s-%(sid)s-%(rid)s-%(lid)s You have sent %(quantity)s %(item)s to %(receiver)s. If not correct please reply: CANCEL %(lid)s" % {
            'quantity': quantity,
            'item': item.name,
            'receiver': receiver.display_full(),
            'd': log.date.strftime("%d%m%y"),
            'sid': sender.id,
            'rid': receiver.id,
            'lid': log.id
        })
        return True

    @keyword(r'dist \@(\w+) (\w+) (\d+)')
    @registered
    def transfer_clinic_chw (self, message, receiver, code, quantity):
        ''' Transfer Drug from Clinic to CHW or CHW to Clinic
            DIST @mdiallo #001 10'''
        
        sender      = StoreProvider.cls().by_mobile(message.peer)
        receiver   = StoreProvider.cls().by_alias(receiver)
        item        = Item.by_code(code)
        if item == None or sender == None or receiver == None:
            message.respond(_(u"Distribution request failed. Either Item ID or CHW alias is wrong."))
            return True

        try:
            return self.do_transfer_drug(message, sender, receiver, item, quantity)
        except ItemNotInStore:
            message.respond(_(u"Distribution request failed. You do not have %(med)s") % {'med': item})
            return True
        except NotEnoughItemInStock:
            message.respond(_(u"Distribution request failed. You can't transfer %(q)s %(it)s to %(rec)s because you only have %(stk)s.") % {'q': quantity, 'it': item.name, 'rec': receiver.display_full(), 'stk': StockItem.objects.get(peer=sender, item=item).quantity})
            return True

    @keyword(r'add (\w+) (\d+) (.+)')
    @registered
    def add_stock (self, message, code, quantity, note):
        
        ''' Add stock for item. Used by main drug distribution point'''
        
        sender      = StoreProvider.cls().by_mobile(message.peer)
        receiver = sender
        #receiver   = StoreProvider.cls().by_alias(receiver)
        item        = Item.by_code(code)
        if item == None or sender == None or receiver == None:
            message.respond(_(u"Distribution request failed. Either Item ID or CHW alias is wrong."))
            return True
        
        try:
            log = add_stock_for_item(receiver=receiver, item=item, quantity=int(quantity))
        
            message.respond("CONFIRMATION #%(d)s-%(sid)s-%(lid)s You have added %(quantity)s %(item)s to your stock. If not correct please reply: CANCEL %(lid)s" % {
            'quantity': quantity,
            'item': item.name,
            'receiver': receiver.display_full(),
            'd': log.date.strftime("%d%m%y"),
            'sid': sender.id,
            'rid': receiver.id,
            'lid': log.id
            })
        except:
            pass

        return True

    def parse_sku_quantities(self, sku_quantities):
        couples  = sku_quantities.split(" %s" % self.drug_code)
        skq = {}
        try:
            for couple in couples:
                x = couple.split(" ")
                code = x[0].replace(self.drug_code, "")
                item = Item.by_code(code)
                if skq.has_key(code) or item == None:
                    raise MalformedRequest
                skq[code]   = {'code': code, 'quantity': int(x[1]), 'item': item}
            return skq
        except IndexError:
            raise MalformedRequest

    @keyword(r'cdist \@(\w+) (.+)')
    @registered
    def bulk_transfer_clinic_chw (self, message, receiver, sku_quantities):
        ''' Transfer Multiple Drugs from Clinic to CHW
            CDIST @mdiallo #001 10 #004 45 #007 32'''

        sender      = StoreProvider.cls().by_mobile(message.peer)
        receiver   = StoreProvider.cls().by_alias(receiver)

        if sku_quantities == None or sender == None or receiver == None:
            message.respond(_(u"Distribution request failed. Either Item IDs or CHW alias is wrong."))
            return True

        try:
            sq  = self.parse_sku_quantities(sku_quantities)
        except MalformedRequest:
            message.respond(_(u"Distribution failed. Syntax error in drugs/quantities statement."))
            return True
        
        success = []
        failures= []
        for code in sq.itervalues():
            try:
                #print u"%(q)s %(c)s" % {'q':code['quantity'], 'c':code['item']}
                self.do_transfer_drug(message, sender, receiver, code['item'], code['quantity'])
                success.append(code)
            except (NotEnoughItemInStock, ItemNotInStore, Exception):
                failures.append(code)
                continue
        
        if failures.__len__() == 0:
            message.respond(_(u"SUMMARY: Multiple Drugs Distribution went through successfuly."))
            return True
        
        if success.__len__() == 0:
            message.respond(_(u"SUMMARY: complete FAILURE. Multiple Drugs Distribution went wrong on all items."))
            return True

        # some failed, some went trough
        details = u""
        for fail in failures:
            details += u"%s, " % fail['item'].name
        details = details[:-2]
        message.respond(_(u"SUMMARY: Some items couldn't be transfered: %(detail)s") % {'detail': details})
        return True

    def stock_for(self, message, provider):
        if provider == None:
            return False
        msg = stock_answer(provider)
        message.respond(msg)
        return msg

    @keyword(r'stock \@(\w+)')
    @admin
    def request_stock (self, message, target):
        ''' Get stock status for someone
            STOCK @mdiallo'''
        
        provider    = StoreProvider.cls().by_alias(target)
        return self.stock_for(message, provider)

    @keyword(r'stock')
    @registered
    def request_self_stock (self, message):
        ''' Get stock status for a store
            STOCK'''
        
        provider    = StoreProvider.cls().by_mobile(message.peer)
        return self.stock_for(message, provider)

    @keyword(r'cancel (\d+)')
    @registered
    def cancel_request (self, message, cancel_id):
        ''' Cancel a transfer request
            CANCEL 908432'''
        
        # retrieve transaction
        try:
            log = TransferLog.objects.get(id=int(cancel_id))
        except TransferLog.DoesNotExist:
            message.respond(_(u"Cancellation failed. Provided transaction ID (%(lid)s) is wrong.") % {'lid': cancel_id})
            return True

        # Check request is legitimate
        peer    = Provider.by_mobile(message.peer).storeprovider_ptr
        if peer == None or (log.sender, log.receiver).count(peer) == 0:
            message.respond(_("Cancellation failed. With all due respect, you are not allowed to perform this action."))
            return True

        # Check is transfer hasn't already been cancelled
        if (TransferLog.STATUS_CANCELLED, TransferLog.STATUS_CONFLICT).count(log.status) != 0 :
            message.respond(_("Cancellation failed. Transfer #%(lid)s dated %(date)s has already been cancelled or is in conflict.") % {'lid': log.id, 'date': log.date.strftime("%b %d %y %H:%M")})
            return True
        
        # cancellation attempt
        other_peer  = log.receiver if peer == log.sender else log.sender
        try:
            cancel_transfer(log)
            msg = _(u"CANCELLED Transfer #%(lid)s dated %(date)s by request of %(peer)s. Please forward conflict to Drug Store Head.") % {'lid': log.id, 'date': log.date.strftime("%b %d %y %H:%M"), 'peer': peer.direct().display_full()}
            message.respond(msg)
            message.forward(other_peer.direct().mobile, msg)
        except (ItemNotInStore, NotEnoughItemInStock):
            # goods has been transfered elsewhere.
            msg = _(u"Cancellation failed. %(peer)s has started distributing drugs from transaction #%(lid)s. Contact Drug Store Head.") % {'lid': log.id, 'peer': peer.direct().display_full()}
            message.respond(msg)
            message.forward(other_peer.direct().mobile, msg)
            return True

        return True

    def outgoing (self, message):
        pass

