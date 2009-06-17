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
        tlz     = Zone.objects.filter(zone=zone)    
        for z in tlz:
            recipients  = recipients_from_zone(z.name, None)
            price       = price_for_msg(recipients, msg_price)
            zo      = {'n': z.name, 'p': price}
            zo['c'] = []
            zo['b'] = []
            bb      = BoardManager.objects.filter(zone=z)
            for board in bb:
                bo  = {'n': board.name, 'c': board.cost, 'p': board.cost * msg_price, 'm': board.mobile, 'd': board.details}
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




