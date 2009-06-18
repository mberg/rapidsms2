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
    (r'^zone_list\/?$', 'apps.billboard.views.zone_list'),
    (r'^medias/(?P<path>.*)$', 'django.views.static.serve', {'document_root': '/work/src/sms/media', 'show_indexes': True}),
    admin_urls
)

