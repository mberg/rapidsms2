# coding=utf-8

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

class Zone(models.Model):
    name        = models.CharField(max_length=10, unique=True)
    full_name   = models.CharField(max_length=50, blank=True, null=True)
    zone        = models.ForeignKey('Zone',verbose_name=_("Parent Zone"), blank=True, null=True, related_name="related_zone")

    def __unicode__(self):
        return self.full_name if not self.full_name == None else self.name

class MemberType(models.Model):
    name        = models.CharField(max_length=20)
    code        = models.CharField(max_length=10)
    fee         = models.IntegerField()
    contrib     = models.IntegerField(_(u'Contribution'))

    def __unicode__(self):
        return self.name

class Member(models.Model):
    class Meta:
        app_label = "billboard"
    user        = models.OneToOneField(User)
    alias       = models.CharField(_("Alias"),max_length=10, unique=True, db_index=True)
    name        = models.CharField(max_length=50,blank=True,null=True)
    mobile      = models.CharField(max_length=16, db_index=True, unique=True)
    membership  = models.ForeignKey(MemberType,verbose_name=_(u'Type'))
    active      = models.BooleanField(default=True)
    credit      = models.IntegerField(default=0)
    rating      = models.IntegerField(_("Rating"), default=1)
    zone        = models.ForeignKey(Zone)
    latitude    = models.CharField(_('Latitude'), max_length=25, blank=True, null=True)
    longitude   = models.CharField(_('Longitude'), max_length=25, blank=True, null=True)
    picture     = models.ImageField(_('Picture'),upload_to='board_pics', blank=True, null=True)
    details     = models.TextField(blank=True)

    def __unicode__(self):
        if self.name != None:
            front   = self.name
        else:
            if self.user.first_name or self.user.last_name:
                front   = "%s %s" % (self.user.first_name, self.user.last_name)
            else:
                return self.alias
        return u'%(front)s (%(alias)s)' % {'front': front, 'alias': self.alias}

    @classmethod
    def by_mobile (cls, mobile):
        try:
            return cls.objects.get(mobile=mobile, active=True)
        except models.ObjectDoesNotExist:
            return None

    @classmethod
    def is_admin(cls, mobile):
        try:
            return cls.objects.get(mobile=mobile,membership=MemberType.objects.get(code='admin'))
        except models.ObjectDoesNotExist:
            return None

class Announcement(models.Model):
    sender      = models.ForeignKey("Member", related_name="%(class)s_related_sender")
    recipients  = models.ManyToManyField("Member", related_name="%(class)s_related_recipients")
    text        = models.CharField(max_length=140)
    date        = models.DateTimeField()
    price       = models.IntegerField(default=0)
    sent        = models.BooleanField()

    def __unicode__(self):
        return "%s (%s)" % (self.sender, self.date.strftime("%c"))

class Configuration(models.Model):
    key     = models.CharField(max_length=16, primary_key=True)
    value   = models.CharField(max_length=100)
    
    def __unicode__(self):
        return self.key

    @classmethod
    def get_dictionary(cls):
        dico    = {}
        for conf in cls.objects.all():
            try:
                dico[conf.key]  = eval(conf.value) # SECURITY: assume good faith?
            except NameError:
                dico[conf.key]  = conf.value
        return dico
        
