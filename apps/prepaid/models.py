# coding=utf-8

from django.db import models
from django.utils.translation import ugettext_lazy as _

class Configuration(models.Model):
    key     = models.CharField(max_length=32, primary_key=True)
    value   = models.CharField(max_length=200, blank=True)
    
    def __unicode__(self):
        return self.key

    @classmethod 
    def get(cls, key):
        try:
            return cls.get_dictionary(cls)[key]
        except:
            return None

    @classmethod
    def get_dictionary(cls):
        dico    = {}
        for conf in cls.objects.all():
            dico[conf.key]  = conf.value
        return dico

class MessageLog(models.Model):
    sender          = models.CharField(max_length=16)
    recipient       = models.CharField(max_length=16)
    text            = models.CharField(max_length=1400)
    date            = models.DateTimeField()

    def __unicode__(self):
        return u"%(sender)s > %(recipient)s: %(text)s" % {'sender': self.sender, 'recipient': self.recipient, 'text':self.text[:20]}

class Record(models.Model):
    TYPE_CHOICES = (
        ('T', 'Top Up'),
        ('B', 'Balance'),
    )

    sender          = models.CharField(max_length=16)
    text            = models.CharField(max_length=1400)
    date            = models.DateTimeField()
    kind            = models.CharField(max_length=1, choices=TYPE_CHOICES,default='B')
    value           = models.FloatField()

    def __unicode__(self):
        return u"%(sender)s> %(kind)s = %(value)s - %(text)s" % {'sender': self.sender, 'kind': self.kind, 'value': self.value, 'text':self.text[:60]}

