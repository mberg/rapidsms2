# coding=utf-8

from apps.billboard.models import *
import datetime
import spomsky
import string
import random
from django.utils.translation import ugettext_lazy as _
import re

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

def modem_logger(modem, message, type):
    if type in (1,2): print "%8s %s" % (type, message)
    pass

class InsufficientCredit(Exception):
    pass 

config  = Configuration.get_dictionary()

def price_fmt(price):
    return u"%(p)s%(c)s" % {'p':price, 'c':config['currency']}

def random_alias():
    return "".join(random.sample(string.letters+string.digits, 10)).lower()

def zonecodes_from_string(zonestring):
    zones   = []
    zonesc   = zonestring.split(',')
    for zone in zonesc:
        if zone.find('@') == 0:
            zone    = zone.__getslice__(1,zone.__len__())
        if zones.count(zone) == 0:
            zones.append(zone)
    return zones

def zone_recipients(zonecode, exclude=None):

    if zonecode.__class__ == str:
        zonecode    = [zonecode]

    recipients  = []

    for zone in zonecode:
        try:
            query_zone  = Zone.objects.get(name=zone)
            all_zones   = recurs_zones(query_zone)
            all_boards  = Member.objects.filter(active=True,membership=MemberType.objects.get(code='board'),zone__in=all_zones)
        except models.ObjectDoesNotExist:
            all_boards  = Member.objects.filter(active=True,membership=MemberType.objects.get(code='board'),alias=zone)

        for board in all_boards.iterator():
            if recipients.count(board) == 0:
                recipients.append(board)

    if not exclude == None:
        try:
            recipients.remove(exclude)
        except:
            pass

    return recipients

def recurs_zones(zone):
    zonelist    = []
    all_zones   = Zone.objects.filter(zone=zone)
    for azone in all_zones.iterator():
        zonelist += recurs_zones(azone)
        zonelist.append(azone)
    zonelist.append(zone)
    return zonelist

def message_cost(sender, recipients, ad=None, fair=False):
    price   = 0
    if not ad == None:
        cost    = ad.price
    else:
        mtype   = sender.membership
        cost    = mtype.fee

    for recip in recipients:
        if fair:
            price   += float(config['fair_price'])
        else:
            price   += (recip.rating * cost)

    return price

def ad_from(content):
    try:
        adt     = re.search('^\s?\+([a-z])', content).groups()[0]
        adt     = AdType.by_code(adt)
    except:
        adt     = None
    return adt


def send_message(backend, sender, recipients, content, action_code=None, adt=None, allow_overdraft=False, fair=False):
    plain_recip     = recipients # save this for record_action
    if recipients.__class__ == str:
        recipients  = Member(alias=random_alias(),rating=1,mobile=recipients,credit=0, membership=MemberType.objects.get(code='alien'))

    if recipients.__class__ == Member:
        recipients  = [recipients]

    cost    = message_cost(sender, recipients, adt, fair)
    if cost > sender.credit and not allow_overdraft:
        raise InsufficientCredit

    mtype   = sender.membership
    contrib = mtype.contrib

    content = _(u"%(alias)s> %(msg)s" % {'alias': sender.alias_display(), 'msg': content})[:160]

    for recipient in recipients:
        if recipient.is_board():
            recipient.credit    += contrib
            recipient.save()

        msg = backend.message(recipient.mobile, content[:160])
        backend._router.outgoing(msg)

        log = MessageLog(sender=sender.mobile,sender_member=sender,recipient=recipient.mobile,recipient_member=recipient,text=content[:140],date=datetime.datetime.now())
        log.save()

    sender.credit   -= cost

    if allow_overdraft:
        if sender.credit < 0:
            sender.credit   = 0

    sender.save()

    if action_code.__class__ == str and action_code != None:
        record_action(action_code, sender, plain_recip, content, cost, adt)

    return cost

def default_tag():
    if not config:
        config      = Configuration.get_dictionary()

    return Tag.by_code(config['dfl_tag_code'])

def record_action(kind, source, target, text, cost, ad=None, date=datetime.datetime.now()):

    if target.__class__ == str:
        target  = Member.system()

    if target.__class__ == Member:
        target  = [target]

    action  = Action(kind=ActionType.by_code(kind), source=source, text=text, date=date, cost=cost, ad=ad)
    action.save()

    for m in target:
        action.target.add(m)

    action.save()
    return action

