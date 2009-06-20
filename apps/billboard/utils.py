# coding=utf-8

from apps.billboard.models import *
import datetime
import spomsky
import string
import random

class InsufficientCredit(Exception):
    pass 

server  = spomsky.Client()

def random_alias():
    return "".join(random.sample(string.letters+string.digits, 10)).lower()

def zone_recipients(zone, exclude=None):
    recipients  = []
    query_zone  = Zone.objects.get(name=zone)
    all_zones   = recurs_zones(query_zone)
    all_boards  = Member.objects.filter(membership=MemberType.objects.get(code='board'),zone__in=all_zones)

    for board in all_boards.iterator():
        recipients.append(board)

    if not exclude == None:
        recipients.remove(exclude)

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


def send_message(sender, recipients, content, allow_overdraft=False):
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

