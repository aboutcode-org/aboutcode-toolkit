# This was taken from http://djangosnippets.org/snippets/2413/
# It is stored in thirdparty as django_snippets_2413.py

import re
from django.template import Library, Node, TemplateSyntaxError
from django.http import QueryDict
from django.utils.encoding import smart_str

register = Library()


@register.tag
def query_string(parser, token):
    """
    Template tag for creating and modifying query strings.

    Syntax:
        {% query_string  [<base_querystring>] [modifier]* [as <var_name>] %}

        modifier is <name><op><value> where op in {=, +, -}

    Parameters:
        - base_querystring: literal query string, e.g. '?tag=python&tag=django&year=2011',
                            or context variable bound to either
                            - a literal query string,
                            - a python dict with potentially lists as values, or
                            - a django QueryDict object
                            May be '' or None or missing altogether.
        - modifiers may be repeated and have the form <name><op><value>.
                           They are processed in the order they appear.
                           name is taken as is for a parameter name.
                           op is one of {=, +, -}.
                           = replace all existing values of name with value(s)
                           + add value(s) to existing values for name
                           - remove value(s) from existing values if present
                           value is either a literal parameter value
                             or a context variable. If it is a context variable
                             it may also be bound to a list.
        - as <var name>: bind result to context variable instead of injecting in output
                         (same as in url tag).

    Examples:
    1.  {% query_string  '?tag=a&m=1&m=3&tag=b' tag+'c' m=2 tag-'b' as myqs %}

        Result: myqs == '?m=2&tag=a&tag=c'

    2.  context = {'qs':   {'tag': ['a', 'b'], 'year': 2011, 'month': 2},
                   'tags': ['c', 'd'],
                   'm': 4,}

        {% query_string qs tag+tags month=m %}

        Result: '?tag=a&tag=b&tag=c&tag=d&year=2011&month=4
    """
    # matches 'tagname1+val1' or 'tagname1=val1' but not 'anyoldvalue'
    mod_re = re.compile(r"^(\w+)(=|\+|-)(.*)$")
    bits = token.split_contents()
    qdict = None
    mods = []
    asvar = None
    bits = bits[1:]
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]
    if len(bits) >= 1:
        first = bits[0]
        if not mod_re.match(first):
            qdict = parser.compile_filter(first)
            bits = bits[1:]
    for bit in bits:
        match = mod_re.match(bit)
        if not match:
            raise TemplateSyntaxError("Malformed arguments to query_string tag")
        name, op, value = match.groups()
        mods.append((name, op, parser.compile_filter(value)))
    return QueryStringNode(qdict, mods, asvar)

class QueryStringNode(Node):
    def __init__(self, qdict, mods, asvar):
        self.qdict = qdict
        self.mods = mods
        self.asvar = asvar
    def render(self, context):
        mods = [(smart_str(k, 'ascii'), op, v.resolve(context))
        for k, op, v in self.mods]
        if self.qdict:
            qdict = self.qdict.resolve(context)
        else:
            qdict = None
            # Internally work only with QueryDict
        qdict = self._get_initial_query_dict(qdict)
        #assert isinstance(qdict, QueryDict)
        for k, op, v in mods:
            qdict.setlist(k, self._process_list(qdict.getlist(k), op, v))
        qstring = qdict.urlencode()
        if qstring:
            qstring = '?' + qstring
        if self.asvar:
            context[self.asvar] = qstring
            return ''
        else:
            return qstring
    def _get_initial_query_dict(self, qdict):
        if not qdict:
            qdict = QueryDict(None, mutable=True)
        elif isinstance(qdict, QueryDict):
            qdict = qdict.copy()
        elif isinstance(qdict, basestring):
            if qdict.startswith('?'):
                qdict = qdict[1:]
            qdict = QueryDict(qdict, mutable=True)
        else:
            # Accept any old dict or list of pairs.
            try:
                pairs = qdict.items()
            except:
                pairs = qdict
            qdict = QueryDict(None, mutable=True)
            # Enter each pair into QueryDict object:
            try:
                for k, v in pairs:
                    # Convert values to unicode so that detecting
                    # membership works for numbers.
                    if isinstance(v, (list, tuple)):
                        for e in v:
                            qdict.appendlist(k,unicode(e))
                    else:
                        qdict.appendlist(k, unicode(v))
            except:
                # Wrong data structure, qdict remains empty.
                pass
        return qdict
    def _process_list(self, current_list, op, val):
        if not val:
            if op == '=':
                return []
            else:
                return current_list
            # Deal with lists only.
        if not isinstance(val, (list, tuple)):
            val = [val]
        val = [unicode(v) for v in val]
        # Remove
        if op == '-':
            for v in val:
                while v in current_list:
                    current_list.remove(v)
        # Replace
        elif op == '=':
            current_list = val
        # Add
        elif op == '+':
            for v in val:
                current_list.append(v)
        return current_list
