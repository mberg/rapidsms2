# coding=utf-8

from django.db.models import Q
from django.template import Template, loader, Context
from apps.billboard.models import *
from apps.billboard.utils import *
from django.http import HttpResponse

def ovload_context(context):
    co  = {'conf': config}
    context.update(co)
    return context

def index(request):
    return HttpResponse(loader.get_template('body.html').render(ovload_context(Context({'me': 'reg'}))))

def help(request):
    print config['service_num']
    return HttpResponse(loader.get_template('help.html').render(ovload_context(Context({}))))

def zone_list(request):

#    config      = Configuration.get_dictionary()

    tree    = []
    def zone_fill(tree, zone):
        dumb_board  = Member(alias=random_alias(),rating=1,mobile='000000',credit=0, membership=MemberType.objects.get(code='board'))
        tlz     = Zone.objects.filter(zone=zone)    
        for z in tlz:
            recipients  = zone_recipients(str(z.name))
            price       = message_cost(dumb_board, recipients)
            zo      = {'n': z.name, 'p': price, 'pf': price_fmt(price)}
            zo['c'] = []
            zo['b'] = []
            bb      = Member.objects.filter(zone=z,membership=MemberType.objects.get(code='board'),active=True)
            for board in bb:
                mc  = message_cost(dumb_board, [board])
                bo  = {'n': board.display_name(), 'c': board.rating, 'p': mc, 'm': board.mobile, 'd': board.details, 'pf': price_fmt(mc)}
                zo['b'].append(bo)
            zone_fill(zo['c'], z)
            tree.append(zo)

    zone_fill(tree, None)

    tb  = loader.get_template('zone_list_block.html')

    def recurs_rend(templ, tree):
        op = ""
        for tr in tree:
            c   = Context({'zone':tr})
            op  += templ.render(c)
            op  += recurs_rend(templ, tr['c'])
        return op

    tbh = recurs_rend(tb, tree)

    t   = Template("{% extends 'body.html' %}{% block title %}List of Boards and Zones{% endblock %} {% block content %}" + tbh + "{% endblock %}")

    c = Context({
        'conf': config,
    })
    return HttpResponse(t.render(ovload_context(c)))

def history(request):
    t   = loader.get_template('history.html')
    c   = Context({'members': Member.objects.filter(membership=MemberType.by_code('board')),
                   'conf': config})
    return HttpResponse(t.render(ovload_context(c)))

def history_one(request, alias):
    member  = Member.objects.get(alias=alias)
    t   = loader.get_template('history_one.html')
    c   = Context({'member': member,
                   'actions': Action.objects.filter(Q(source=member)),
                   'conf': config})
    return HttpResponse(t.render(ovload_context(c)))


