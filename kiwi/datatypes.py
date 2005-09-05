#
# Kiwi: a Framework and Enhanced Widgets for Python
#
# Copyright (C) 2005 Async Open Source
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
# USA
# 
# Author(s): Lorenzo Gil Sanchez <lgs@sicem.biz>
#            Gustavo Rahal <gustavo@async.com.br>
#            Johan Dahlin <jdahlin@async.com.br>
#

from datetime import date
import locale
import time

__all__ = ['ValidationError', 'lformat', 'converter']

class ValidationError(Exception):
    pass

# by default locale uses the C locale but our date conversions use the user
# locale so we need to set the locale to that one
locale.setlocale(locale.LC_ALL, '') # this set the user locale ( $LANG )

def lformat(format, value):
    return locale.format(format, value, 1)

class ConverterRegistry:
    def __init__(self):
        self._converters = {}

    def add(self, converter_type):
        c = converter_type()
        self._converters[c.type] = c

    def get_supported_types(self):
        return self._converters.values()

    def get_supported_type_names(self):
        return [t.type.__name__ for t in self._converters.values()]

    def get_list(self):
        return self._converters.values()

    def as_string(self, converter_type, data, *args, **kwargs):
        c = self._converters[converter_type]
        if c.as_string is None:
            return data

        assert isinstance(data, c.type), ('data "%s" must be of %r not %r' % (
            data, c.type, type(data)))
        
        return c.as_string(data, *args, **kwargs)
            
    def from_string(self, converter_type, data, *args, **kwargs):
        c = self._converters[converter_type]
        if c.from_string is None:
            return data

        return c.from_string(data, *args, **kwargs)

    def str_to_type(self, value):
        for c in self._converters.values():
            if c.type.__name__ == value:
                return c.type

# Global converter, can be accessed from outside
converter = ConverterRegistry()


class StringConverter:
    type = str

    def from_string(self, value):
        return str(value)
    
    def as_string(self, value, format='%s'):
        return format % value

converter.add(StringConverter)

class IntConverter:
    type = int

    def as_string(self, value, format='%d'):
        """Convert a float to a string"""
        return lformat(format, value)

    def from_string(self, value):
        "Convert a string to an integer"
        try:
            return int(value)
        except ValueError:
            raise ValidationError("This field requires an integer number")
converter.add(IntConverter)
    
class BoolConverter:
    type = bool
    
    as_string = lambda s, value, format=None: str

    def from_string(self, value, default_value=True):
        "Convert a string to a boolean"
        if value.upper() in ('TRUE', '1'):
            return True
        elif value.upper() in ('FALSE', '0'):
            return False
        else:
            return default_value
converter.add(BoolConverter)

class FloatConverter:
    type = float
    
    def __init__(self):
        self._locale_dictionary = locale.localeconv()
        
    def as_string(self, value, format='%f'):
        """Convert a float to a string"""
        return lformat(format, value)

    def from_string(self, value):
        """Convert a string to a float"""
        th_sep = self._locale_dictionary["thousands_sep"]
        dec_sep = self._locale_dictionary["decimal_point"]
    
        # XXX: HACK! did this because lang like pt_BR and es_ES are
        #            considered to not have a thousand separator
        if th_sep == "":  
            th_sep = '.'

        th_sep_count = value.count(th_sep)
        dec_sep_count = value.count(dec_sep)
        if th_sep_count > 0 or dec_sep_count > 0:
            # we have separators
            if dec_sep_count > 1:
                raise ValidationError(
                    'You have more than one decimal separator ("%s") '
                    ' in your number "%s"' % (dec_sep, value))

            if th_sep_count > 0 and dec_sep_count > 0:
                # check if the dec separator is to right of every th separator
                dec_pos = value.index(dec_sep)
                th_pos = value.find(th_sep)
                while th_pos != -1:
                    if dec_pos < th_pos:
                        raise ValidationError(
                            "The decimal separator is to the left of "
                            "the thousand separator")
                    th_pos = value.find(th_sep, th_pos+1)
        value = value.replace(th_sep, '')
        value = value.replace(dec_sep, '.')
        try:
            return float(value)
        except ValueError:
            raise ValidationError("This field requires a number")
converter.add(FloatConverter)

class DateConverter:
    type = date
    
    def __init__(self):
        self.update_format()

    def update_format(self):
        self._format = locale.nl_langinfo(locale.D_FMT)

    def as_string(self, value, format=None):
        "Convert a date to a string"
        if format is None:
            format = self._format
            
        return value.strftime(format)
    
    def from_string(self, value):
        "Convert a string to a date"
        
        # We're only supporting strptime values for now,
        # perhaps we should add macros, to be able to write
        # yyyy instead of %Y
        
        try:
            dateinfo = time.strptime(value, self._format)
            return date(*dateinfo[:3]) # year, month, day
        except ValueError:
            raise ValidationError('This field requires a date of '
                                  'the format "%s"' % self._format)
converter.add(DateConverter)

class ObjectConverter:
    type = object
    
    as_string = None
    from_string = None
converter.add(ObjectConverter)

def format_price(value, symbol=True):
    """
    Formats a price according to the current locales monetary
    settings
    
    @param value: number
    @param symbol: whether to include the currency symbol
    """
    
    opt = locale.localeconv()
    mon_grouping = opt.get('mon_grouping', [])
    mon_thousands_sep = opt.get('mon_thousands_sep', '.')
    mon_decimal_point = opt.get('mon_decimal_point', '.')
    p_cs_precedes = opt.get('p_cs_precedes', 1)
    n_cs_precedes = opt.get('n_cs_precedes', p_cs_precedes)
    currency_symbol = opt.get('currency_symbol', '')
    frac_digits = opt.get('frac_digits', 2)
    p_sep_by_space = opt.get('p_sep_by_space', 1)
    n_sep_by_space = opt.get('n_sep_by_space', p_sep_by_space)
    positive_sign = opt.get('positive_sign', '')
    negative_sign = opt.get('negative_sign', '-')

    # Patching glibc's output
    # See http://sources.redhat.com/bugzilla/show_bug.cgi?id=1294
    current_locale = locale.getlocale(locale.LC_MONETARY)
    if current_locale[0] == 'pt_BR':
        p_cs_precedes = n_cs_precedes = 1
        p_sep_by_space = n_sep_by_space = 0

    # Pythons string formatting can't handle %.127f
    if frac_digits == 127:
        frac_digits = 2

    
    if value > 0:
        cs_precedes = p_cs_precedes
        sep_by_space = p_sep_by_space
        sign = positive_sign
    else:
        cs_precedes = n_cs_precedes
        sep_by_space = n_sep_by_space
        sign = negative_sign

    # Grouping (eg thousand separator) of decimal part
    groups = mon_grouping[:]
    groups.reverse()
    if groups:
        group = groups.pop()
    else:
        group = 3

    intparts = []
    intpart = str(int(abs(value)))

    while True:
        if not intpart:
            break
        
        s = intpart[-group:]
        intparts.insert(0, s)
        intpart = intpart[:-group]
        
        if not groups:
            continue
        
        last = groups.pop()
        # if 0 reuse last one
        if last != 0:
            group = last

    retval = sign + mon_thousands_sep.join(intparts)
        
    # Only add decimal part if it has one, is this correct?
    if value % 1 != 0:
        format = '%%.%sf' % frac_digits
        dec_part = (format % value)[-frac_digits:]
        retval += mon_decimal_point + dec_part

    if currency_symbol and symbol:
        if sep_by_space:
            space = ' '
        else:
            space = ''
        if cs_precedes:
            retval = currency_symbol + space + retval
        else:
            retval = retval + space + currency_symbol
        
    return retval
