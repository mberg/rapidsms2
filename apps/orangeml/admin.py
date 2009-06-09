
from django.contrib import admin
from models import Transaction
from datetime import datetime

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('mobile', 'amount', 'date')
    list_filter = ['date','mobile','amount']
    search_fields = ['mobile','amount']
    actions = ['delete_selected']

admin.site.register(Transaction, TransactionAdmin)

