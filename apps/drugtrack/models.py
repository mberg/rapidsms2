# coding=utf-8

from django.db import models
from django.contrib.auth.models import User
from apps.tinystock.models import StoreProvider, KindOfItem, Item, StockItem
from django.utils.translation import ugettext_lazy as _
from datetime import datetime

class Zone(models.Model):

    def __unicode__ (self): 
        return self.name

    class Meta:
        app_label = "drugtrack"
    
    CLUSTER_ZONE = 1
    VILLAGE_ZONE = 2
    SUBVILLAGE_ZONE = 3
    ZONE_TYPES = (
        (CLUSTER_ZONE, _('Cluster')),
        (VILLAGE_ZONE, _('Village')),
        (SUBVILLAGE_ZONE, _('Sub village'))
    )
    
    alias       = models.CharField(max_length=16, unique=True, db_index=True)
    name        = models.CharField(max_length=255)
    head        = models.ForeignKey("self", null=True,blank=True)
    category    = models.IntegerField(choices=ZONE_TYPES, default=VILLAGE_ZONE)
    lon         = models.FloatField(null=True,blank=True)
    lat         = models.FloatField(null=True,blank=True)

class Facility(models.Model):

    def __unicode__ (self): 
        return self.name
        
    class Meta:
        verbose_name_plural = "Facilities"
        app_label = "drugtrack"

    CLINIC_ROLE  = 1
    DISTRIB_ROLE = 2
    ROLE_CHOICES = (
        (CLINIC_ROLE,  _('Clinic')),
        (DISTRIB_ROLE, _('Distribution Point')),
    )
    
    alias       = models.CharField(max_length=16, unique=True, db_index=True)
    name        = models.CharField(max_length=255)
    role        = models.IntegerField(choices=ROLE_CHOICES, default=CLINIC_ROLE)
    zone        = models.ForeignKey(Zone,db_index=True)
    lon         = models.FloatField(null=True,blank=True)
    lat         = models.FloatField(null=True,blank=True)

    def display_name(self):
        if self.name:
            return self.name
        if self.alias:
            return self.alias
        else:
            return str(self.id)

    @classmethod
    def by_alias (cls, alias):
        try:
            return cls.objects.get(alias=alias)
        except models.ObjectDoesNotExist:
            return None

class Provider(StoreProvider):

    class Meta:
        app_label = "drugtrack"
    
    CHW_ROLE    = 1
    PHA_ROLE  = 2
    
    ROLE_CHOICES = (
        (CHW_ROLE,    _('CHW')),
        (PHA_ROLE,  _('Pharmacist')),
    )
    
    alias       = models.CharField(max_length=16, unique=True, db_index=True)
    mobile      = models.CharField(max_length=16, unique=True, null=True, db_index=True)
    first_name  = models.CharField(max_length=32, null=True, blank=True)
    last_name   = models.CharField(max_length=32, null=True, blank=True)
    role        = models.IntegerField(choices=ROLE_CHOICES, default=CHW_ROLE)
    active      = models.BooleanField(default=True)
    clinic      = models.ForeignKey(Facility, null=True, blank=True, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    admin       = models.BooleanField(default=False)

    def display_name(self):
        if self.first_name or self.last_name:
            return "%s %s" % (self.first_name, self.last_name)
        if self.alias:
            return self.alias
        if self.mobile:
            return str(self.mobile)
        else:
            return str(self.id)

    def display_full(self):
        if not self.clinic or self.role == self.CHW_ROLE:
            return self.display_name()
        return _(u"%(n)s at %(p)s") % {'n': self.display_name(), 'p': self.clinic.name}

    def __unicode__(self):
        return self.display_name()
    
    def get_dictionary(self):
        return {
                "first_name": self.first_name,
                "last_name": self.last_name.upper(),
                "id": self.id,
                "mobile": self.mobile,
                "provider_mobile": self.mobile,
                "name": self.get_name_display(),
                "clinic": self.clinic.name,
                "alias": self.alias
            }
    
    @classmethod
    def by_alias (cls, alias):
        try:
            return cls.objects.get(alias=alias)
        except models.ObjectDoesNotExist:
            return None

    @classmethod
    def by_mobile (cls, mobile):
        try:
            return cls.objects.get(mobile=mobile, active=True)
        except models.ObjectDoesNotExist:
            return None

StoreProvider.set_class(Provider, 'provider')

class Patient(StoreProvider):

    class Meta:
        app_label = "drugtrack"
    
    SEXE_MALE    = 1
    SEXE_FEMALE = 2
    
    SEXE_CHOICES = (
        (SEXE_MALE,    _('Male')),
        (SEXE_FEMALE,  _('Female')),
    )
    
    first_name  = models.CharField(max_length=32, null=True, blank=True)
    last_name   = models.CharField(max_length=32, null=True, blank=True)
    sexe        = models.IntegerField(choices=SEXE_CHOICES, default=SEXE_MALE)
    created_at  = models.DateTimeField(auto_now_add=True)
    age         = models.IntegerField()
    
    def display_name(self):
        if self.first_name or self.last_name:
            return "%s %s" % (self.first_name, self.last_name)
        else:
            return str(self.id)

    def display_full(self):
        return self.display_name()

    def __unicode__(self):
        return self.display_name()

    def display_age(self):
        if self.age < 12:
            return _(u"%(age)sm") % {'age': self.age}
        else:
            return _(u"%(age)sy") % {'age': self.age}

    @classmethod
    def age_from_str (cls, stra):
        age = 0
        try:
            if stra[-1] == 'y':
                age = int(stra[:-1]) * 12
            elif stra[-1] == 'm':
                age = int(stra[:-1])
            else:
                age = int(stra)
        except:
            age = 0
        return age

#StoreProvider.set_class(Patient, 'patient')
