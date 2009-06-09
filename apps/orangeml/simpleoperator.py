import rapidsms
import re

def _(txt): return txt

class SimpleOperatorApp (rapidsms.app.App):

    operator_numbers  = [] # to be overloaded

    # to be overloaded
    def valid_message(self, message):
        return False

    # to be overloaded. Return true to stop message progression.
    def record_operation(self, message):
        return False

    def is_operator_message(self, message):
        return self.operator_numbers.count(message.peer) > 0

    def start (self):
        pass

    def parse (self, message):
        """Check if message is from Operator"""
        message.operator  = self.is_operator_message(message)

    def handle (self, message):
        if not message.operator:
            return False

        if not self.valid_message(message): # non-credit message
            return False
        else: # working message. forwarded to subclass
            return self.record_operation(message)

