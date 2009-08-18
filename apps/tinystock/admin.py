# coding=utf-8

from django.contrib import admin
from datetime import datetime
from django.utils.translation import ugettext as _
from models import TransferLog, KindOfItem, Item, StockItem, StoreProvider

admin.site.register(KindOfItem)
admin.site.register(Item)
admin.site.register(StockItem)
#admin.site.register(StoreProvider)
admin.site.register(TransferLog)

