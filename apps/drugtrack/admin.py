# coding=utf-8

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import ugettext as _
from models import Zone, Facility, Provider, User

admin.site.register(Provider)
admin.site.register(Zone)
admin.site.register(Facility)
