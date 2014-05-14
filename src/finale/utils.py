import re

isin = re.compile("^[A-Z]{2}[A-Z0-9]{10,11}$")

def is_isin(code):
    return isin.match(code)