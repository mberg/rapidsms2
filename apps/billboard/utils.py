# coding=utf-8

from apps.billboard.models import *

def recipients_from_zone(zone, exclude=None):
    recipients  = []
    query_zone  = Zone.objects.get(name=zone)
    all_zones   = recurs_zones(query_zone)
    all_boards  = BoardManager.objects.filter(zone__in=all_zones)

    for board in all_boards.iterator():
        recipients.append(board.mobile)

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

def price_for_msg(recipients, bulk):
    price   = 0
    for recip in recipients:
        bm      = BoardManager.by_mobile(recip)
        price   += (bm.cost * bulk)
    return price
