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

class AnnouncementAdmin(admin.ModelAdmin):

    class Meta:
        ordering = ["date"]

    list_display = ('sender', 'date', 'price','sent')
    list_filter = ['sender','date','sent']
    search_fields = ['sender','text','recipients']

class ZoneAdmin(admin.ModelAdmin):
    list_filter = ['zone']

class MemberTypeAdmin(admin.ModelAdmin):
    pass

class MemberAdmin(admin.ModelAdmin):
    list_display    = ('__unicode__', 'alias', 'mobile', 'membership', 'credit', 'rating', 'zone', 'active')
    list_filter     = ['membership','zone','active']
    fieldsets = (
        (_('Board'), {'fields': ('user', 'alias', 'name', 'mobile', 'membership', 'credit', 'rating', 'active')}),
        (_('Location'), {'fields': ('zone', ('latitude', 'longitude'), 'details', 'picture')}),
    )
    actions =  actions = ['delete_selected','make_activated']

    def make_activated(self, request, queryset):
        rows_updated = queryset.update(active=True)
        if rows_updated == 1:
            message_bit = "1 member was"
        else:
            message_bit = "%s members were" % rows_updated
        self.message_user(request, "%s successfully activated." % message_bit)

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, MemberUserAdmin)

admin.site.register(MemberType, MemberTypeAdmin)
admin.site.register(Member, MemberAdmin)
admin.site.register(Zone, ZoneAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(Configuration)
