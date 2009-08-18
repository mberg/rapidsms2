# coding=utf-8

from django.utils.translation import ugettext as _
from models import Zone, Facility, Provider, User
from apps.tinystock.models import StoreProvider, KindOfItem, Item, StockItem

def stock_answer(target):
    if target.total() == 0:
        return _(u"%(user)s has nothing") % {'user': target.direct().display_name()}
 
    answer  = _(u"%(user)s has: ") % {'user': target.direct().display_name()}
    sep     = u", "
    stock   = target.store()
    for couple in stock:
        answer += _(u"%(med)s (#%(k)s%(sku)s): %(q)s") % {'med': couple.item.name, 'q': couple.quantity, 'k': couple.item.kind.code, 'sku': couple.item.sku}
        answer += sep
    return answer[:-sep.__len__()]
