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
    picture     = models.ImageField(_('Picture'), upload_to='board_pics', blank=True, null=True)
    details     = models.TextField(blank=True)

    def __unicode__(self):
        return self.display_name()

    def display_name(self):
        if self.name != None:
            front   = self.name
        else:
            if self.user.first_name or self.user.last_name:
                front   = "%s %s" % (self.user.first_name, self.user.last_name)
            else:
                return self.alias
        return u'%(front)s (%(alias)s)' % {'front': front, 'alias': self.alias}

    def is_board(self):
        return bool(self.membership == MemberType.objects.get(code='board'))

    def is_admin(self):
        return bool(self.membership == MemberType.objects.get(code='admin'))

    def alias_zone(self):
        return u"@%(alias)s (@%(zone)s)" % {'alias': self.alias, 'zone': self.zone.name}

    @classmethod
    def by_mobile (cls, mobile):
        try:
            return cls.objects.get(mobile=mobile, active=True)
        except models.ObjectDoesNotExist:
            return None

    @classmethod
    def system(cls):
        return cls.objects.get(alias='sys')

    @classmethod
    def active_boards(cls):
        ba  = []        
        ab  = cls.objects.filter(membership=MemberType.objects.get(code='board'),active=True)
        for b in ab:
            ba.append(b)
        return ba

class ActionType(models.Model):
    code        = models.CharField(max_length=25,primary_key=True)
    name        = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    @classmethod
    def by_code (cls, code):
        try:
            return cls.objects.get(code=code)
        except models.ObjectDoesNotExist:
            return None

class Action(models.Model):
    kind        = models.ForeignKey("ActionType")
    source      = models.ForeignKey("Member", related_name="%(class)s_related_source")
    target      = models.ManyToManyField("Member", related_name="%(class)s_related_target",blank=True)
    text        = models.CharField(max_length=140)
    date        = models.DateTimeField()
    cost        = models.IntegerField(default=0)
    tags        = models.ManyToManyField("Tag",null=True,blank=True)

    def __unicode__(self):
        return u"%(from)s %(kind)s (%(cost)s)" % {'from': self.source.alias, 'kind': self.kind, 'cost':self.cost}

    def targets(self):
        if self.target.count() == 0:
            return "None"
        elif self.target.count() > 0:
            #return self.target.count()
            s   = self.target.select_related()[0].__unicode__()
            if self.target.count() > 1:
                s   += " (%s)" % self.target.count().__str__()
            return s

class Tag(models.Model):
    code        = models.CharField(max_length=2, unique=True)
    name        = models.CharField(max_length=30)

    def __unicode__(self):
        return self.name

    @classmethod
    def by_code (cls, code):
        try:
            return cls.objects.get(code=code)
        except models.ObjectDoesNotExist:
            return None

    @classmethod
    def find_or_create (cls, code):
        try:
            return cls.objects.get(code=code)
        except models.ObjectDoesNotExist:
            t   = Tag(code=code,name=code)
            t.save()
            return t

class MessageLog(models.Model):
    sender      = models.CharField(max_length=16)
    sender_member   =  models.ForeignKey("Member", blank=True, null=True, related_name="%(class)s_related_sender")
    recipient   = models.CharField(max_length=16)
    recipient_member=  models.ForeignKey("Member", blank=True, null=True, related_name="%(class)s_related_recipients")
    text        = models.CharField(max_length=140)
    date        = models.DateTimeField()

    def __unicode__(self):
        sender      = self.sender_member.alias if self.sender_member else self.sender
        recipient   = self.recipient_member.alias if self.recipient_member else self.recipient
        return u"%(sender)s > %(recipient)s: %(text)s" % {'sender': sender, 'recipient':recipient, 'text':self.text[:20]}

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
        
