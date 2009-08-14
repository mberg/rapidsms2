# coding=utf-8

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from datetime import datetime

class StoreProvider(models.Model):


    _direct         = None
    _direct_class   = None

    @classmethod
    def set_class(cls, sub_cls, sub_cls_str):
        cls._direct        = eval("cls.%s" % sub_cls_str)
        cls._direct_class  = sub_cls

    def direct(self):
        return self._direct

    def cls(self):
        return self._direct_class

    def __unicode__(self):
        return u"%s (%s)" % (self.direct(), self.total())

    def store(self):
        return StockItem.objects.filter(peer=self)

    def total(self):
        total = self.store().extra(select={'total': 'SUM(quantity)'})[0].total
        if total == None:
            total = 0
        return total

    @classmethod
    def cls(cls):
        return cls._direct_class

class KindOfItem(models.Model):
    ''' Primary categorization of an item.
        can be 'Tablet' or 'Dose' in a health context.
        code PK allows sms lookup'''
    code    = models.CharField(max_length=16, primary_key=True)
    name    = models.CharField(max_length=64)

    def __unicode__(self):
        return u"%(n)s (%(c)s)" % {'n': self.name, 'c': self.code}

class Item(models.Model):
    ''' Items to be stored. Think it as Drug'''
    sku     = models.CharField(max_length=64, primary_key=True)
    code    = models.CharField(max_length=16, unique=True)
    kind    = models.ForeignKey('KindOfItem')
    name    = models.CharField(max_length=64)

    def __unicode__(self):
        return self.display_name() #u"<%(sku)s:%(txt)s>" % {'sku': self.sku, 'txt': self.name[:30]}

    def display_name(self):
        return u"%(name)s (%(kind)s#%(code)s)" % {'name': self.name, 'code': self.code, 'kind': self.kind.code}

    @classmethod
    def by_sku (cls, sku):
        try:
            return cls.objects.get(sku=sku)
        except models.ObjectDoesNotExist:
            return None

    @classmethod
    def by_code (cls, code):
        try:
            return cls.objects.get(code=code)
        except models.ObjectDoesNotExist:
            return None

class StockItem(models.Model):
    ''' combination of an Item and a quantity '''

    class Meta:
        unique_together = (("peer", "item"),)

    peer    = models.ForeignKey('StoreProvider')
    item    = models.ForeignKey('Item')
    quantity= models.IntegerField()

    def __unicode__(self):
        return u"%(peer)s, %(item)s: %(q)s %(kind)s" % {'q': self.quantity, 'kind': self.item.kind.name, 'item': self.item.name, 'peer': self.peer.direct()}

class TransferLog(models.Model):

    STATUS_OK           = 1
    STATUS_CANCELLED    = 2
    STATUS_CONFLICT     = 3
    
    STATUS_CHOICES = (
        (STATUS_OK,         _('Processed')),
        (STATUS_CANCELLED,  _('Cancelled')),
        (STATUS_CONFLICT,   _('Conflict')),
    )
    
    date    = models.DateTimeField(auto_now_add=True)
    sender  = models.ForeignKey('StoreProvider', related_name="transfer_sender")
    receiver= models.ForeignKey('StoreProvider', related_name="transfer_receiver")
    item    = models.ForeignKey('Item')
    quantity= models.IntegerField()
    status  = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_OK)
    
    def __unicode__(self):
        return u"%(d)s: %(s)s>%(r)s - %(q)s %(it)s" % {'s': self.sender.direct(), 'r': self.receiver.direct(), 'q': self.quantity, 'it': self.item.name, 'd': self.date.strftime("%Y%m%d")}


