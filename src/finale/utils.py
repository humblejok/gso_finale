import re

isin = re.compile("^[A-Z]{2}[A-Z0-9]{10,11}$")

def is_isin(code):
    return isin.match(code)

def to_bloomberg_code(code, terminal=False):
    if is_isin(code):
        return ('/isin/' + code) if terminal else (code+'|ISIN|')
    else:
        return code