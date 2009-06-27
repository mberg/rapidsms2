# coding=utf-8

from apps.billboard.models import *
import datetime
import spomsky
import string
import random

class InsufficientCredit(Exception):
    pass 

server  = spomsky.Client()
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
            print query_zone
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

def message_cost(sender, recipients):
    price   = 0
    mtype   = sender.membership
    cost    = mtype.fee
    for recip in recipients:
        price   += (recip.rating * cost)
    return price


def send_message(sender, recipients, content, action_code=None, allow_overdraft=False):
    plain_recip     = recipients # save this for record_action
    if recipients.__class__ == str:
        recipients  = Member(alias=random_alias(),rating=1,mobile=recipients,credit=0, membership=MemberType.objects.get(code='alien'))

    if recipients.__class__ == Member:
        recipients  = [recipients]

    cost    = message_cost(sender, recipients)
    if cost > sender.credit and not allow_overdraft:
        raise InsufficientCredit

    mtype   = sender.membership
    contrib = mtype.contrib
    for recipient in recipients:
        if recipient.is_board():
            recipient.credit    += contrib
            recipient.save()

        server.send(recipient.mobile, content[:140])
        log = MessageLog(sender=sender.mobile,sender_member=sender,recipient=recipient.mobile,recipient_member=recipient,text=content[:140],date=datetime.datetime.now())
        log.save()

    sender.credit   -= cost

    if allow_overdraft:
        if sender.credit < 0:
            sender.credit   = 0

    if action_code.__class__ == str and action_code != None:
        record_action(action_code, sender, plain_recip, content, cost)

    return cost

def default_tag():
    if not config:
        config      = Configuration.get_dictionary()

    return Tag.by_code(config['dfl_tag_code'])

def record_action(kind, source, target, text, cost, tags=[], date=datetime.datetime.now()):

    if target.__class__ == str:
        target  = Member.system()

    if target.__class__ == Member:
        target  = [target]

    action  = Action(kind=ActionType.by_code(kind), source=source, text=text, date=date, cost=cost)
    action.save()

    for m in target:
        action.target.add(m)

    for t in tags:
        if t.__class__  == str:
            tag = Tag.by_code(t)
            if tag  == None:
                continue
        elif t.__class__    == Tag:
            tag = t
        action.tags.add(tag)
    action.save()
    return action

