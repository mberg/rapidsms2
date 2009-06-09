
from django.db import models
from datetime import datetime

class Transaction(models.Model):

    mobile  = models.CharField(max_length=16, db_index=True)
    amount  = models.IntegerField(default=0)
    date    = models.DateTimeField(auto_now_add=True,editable=True)

    def __unicode__ (self): 
        return "%s - %dF (%s)" % (self.date.strftime("%c"), self.amount, self.mobile)

    def add_credit(self, amount):
        self.credit += amount
        return self.save()

    def reset(self):
        self.credit = 0
        return self.save()

