# coding=utf-8

from django.template import Template, loader, Context
from apps.billboard.models import *
from apps.billboard.utils import *
from django.http import HttpResponse

def index(request):
    return HttpResponse("Hello, world.")

def zone_list(request):

    config      = Configuration.get_dictionary()
    msg_price   = config['price_per_board']

    tree    = []
    def zone_fill(tree, zone):
        dumb_board  = Member(alias='xxxxxxxxxxxxxxxxxx',rating=1,mobile='000000',credit=10000, membership=MemberType.objects.get(code='board'))
        tlz     = Zone.objects.filter(zone=zone)    
        for z in tlz:
            recipients  = zone_recipients(z.name, None)
            price       = message_cost(dumb_board, recipients)
            zo      = {'n': z.name, 'p': price}
            zo['c'] = []
            zo['b'] = []
            bb      = Member.objects.filter(zone=z,membership=MemberType.objects.get(code='board'),active=True)
            for board in bb:
                bo  = {'n': board.display_name(), 'c': board.rating, 'p': board.rating * msg_price, 'm': board.mobile, 'd': board.details}
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

    t   = Template("{% extends 'zone_list.html' %} {% block zone %}" + tbh + "{% endblock %}")

    c = Context({
        'service_num': config['service_num'],
    })
    return HttpResponse(t.render(c))




