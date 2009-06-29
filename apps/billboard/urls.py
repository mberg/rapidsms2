# coding=utf-8

from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

try:
    admin_urls = (r'^admin/', include(admin.site.urls))
except AttributeError:
    # Django 1.0 admin site
    admin_urls = (r'^admin/(.*)', admin.site.root)

urlpatterns = patterns('',
    (r'^$', 'apps.billboard.views.index'),
    (r'^zones\/?$', 'apps.billboard.views.zone_list'),
    (r'^history\/$', 'apps.billboard.views.history'),
    (r'^history\/([a-z0-9]+)$', 'apps.billboard.views.history_one'),
    (r'^help\/$', 'apps.billboard.views.help'),
    (r'^style/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/work/src/sms/apps/billboard/templates/style', 'show_indexes': True}),
    (r'^medias/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/work/src/sms/media', 'show_indexes': True}),
    admin_urls
)

