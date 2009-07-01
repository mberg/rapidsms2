# coding=utf-8

from django.contrib import admin
from models import *
from datetime import datetime
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

class MemberInline (admin.StackedInline):
    model   = Member
    fk_name = 'user'
    max_num = 1

    fieldsets = (
        (_('Board'), {'fields': ('alias', 'name', 'mobile', 'membership', 'credit', 'active', 'zone')}),
    )
    list_filter = ['zone']

class MemberUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'classes': ('collapse',), 'fields': ('is_staff', 'is_active', 'is_superuser')}),
        (_('Groups'), {'classes': ('collapse',), 'fields': ('groups',)}),
    )
    inlines     = (MemberInline,)
    list_filter = ['is_active']

class ZoneAdmin(admin.ModelAdmin):
    list_filter = ['zone']
    ordering = ('id',)

class MemberTypeAdmin(admin.ModelAdmin):
    pass

class MessageLogAdmin(admin.ModelAdmin):
    list_display    = ('__unicode__', 'date')
    list_filter     = ['date','sender']
    ordering = ('-date',)


class MemberAdmin(admin.ModelAdmin):
    list_display    = ('__unicode__', 'alias', 'mobile', 'membership', 'credit', 'rating', 'zone', 'active')
    list_filter     = ['membership','zone','active']
    fieldsets = (
        (_('Board'), {'fields': ('user', 'alias', 'name', 'mobile', 'membership', 'credit', 'rating', 'active')}),
        (_('Location'), {'fields': ('zone', ('latitude', 'longitude'), 'details', 'picture')}),
    )
    actions =  actions = ['delete_selected','make_activated']
    ordering = ('alias',)

    def make_activated(self, request, queryset):
        rows_updated = queryset.update(active=True)
        if rows_updated == 1:
            message_bit = "1 member was"
        else:
            message_bit = "%s members were" % rows_updated
        self.message_user(request, "%s successfully activated." % message_bit)

class ActionTypeAdmin(admin.ModelAdmin):
    list_display    = ('code', 'name')
    ordering = ('code',)

class ActionAdmin(admin.ModelAdmin):
    list_display    = ('__unicode__', 'date', 'cost','targets')
    list_filter     = ['date','kind']
    ordering = ('-id',)

class TagAdmin(admin.ModelAdmin):
    pass

class ConfigurationAdmin(admin.ModelAdmin):
    list_display    = ('__unicode__', 'value')
    ordering = ('key',)

# registrations
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, MemberUserAdmin)

admin.site.register(MessageLog, MessageLogAdmin)
admin.site.register(MemberType, MemberTypeAdmin)
admin.site.register(Member, MemberAdmin)
admin.site.register(Zone, ZoneAdmin)
admin.site.register(Configuration, ConfigurationAdmin)
admin.site.register(ActionType, ActionTypeAdmin)
admin.site.register(Action, ActionAdmin)
admin.site.register(Tag, TagAdmin)
