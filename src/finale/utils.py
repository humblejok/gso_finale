import re

isin = re.compile("^[A-Z]{2}[0-9]{10}$")

def is_isin(code):
    return isin.match(code)