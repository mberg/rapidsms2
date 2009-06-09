
from django.contrib import admin
from models import BoardTigi
from models import Announcement
from models import Zone
from models import SysAdmin
from datetime import datetime

class BoardTigiAdmin(admin.ModelAdmin):

    class Meta:
        ordering = ["name"]

    list_display = ('name', 'mobile', 'credit', 'zone', 'active')
    list_filter = ['zone','credit','active']
    search_fields = ['name','mobile']
    actions =  actions = ['delete_selected','make_activated']

    def make_activated(self, request, queryset):
        rows_updated = queryset.update(active=True)
        if rows_updated == 1:
            message_bit = "1 tigi was"
        else:
            message_bit = "%s tigis were" % rows_updated
        self.message_user(request, "%s successfully activated." % message_bit)


class AnnouncementAdmin(admin.ModelAdmin):

    class Meta:
        ordering = ["date"]

    list_display = ('sender', 'date', 'price','sent')
    list_filter = ['sender','date','sent']
    search_fields = ['sender','text','recipients']

class SysAdminAdmin(admin.ModelAdmin):
    list_display = ('name','mobile')

admin.site.register(Zone)
admin.site.register(SysAdmin, SysAdminAdmin)
admin.site.register(BoardTigi, BoardTigiAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
