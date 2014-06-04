import re

isin = re.compile("^[A-Z]{2}[A-Z0-9]{10,11}$")
bbgid = re.compile("^BBG[A-Z0-9]{9,11}")

def is_isin(code):
    return isin.match(code)

def is_bbgid(code):
    return bbgid.match(code)

def to_bloomberg_code(code, terminal=False):
    if is_isin(code):
        return ('/isin/' + code) if terminal else (code+'|ISIN|')
    elif is_bbgid(code):
        return ('/bbgid/' + code) if terminal else (code+'|BBGID|')
    else:
        return code