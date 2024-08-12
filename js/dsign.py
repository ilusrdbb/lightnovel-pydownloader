import re


def js_dsign(js):
    js = js[31:-9]
    for st in ['window', 'location', "'assign'", "'href'", "'replace'"]:
        equal = re.findall('[_A-Za-z0-9 =]+%s;' % st, js)
        if not equal:
            continue
        else:
            equal = equal[0]
        var = equal.split('=')[0].strip()
        js = js.replace(equal, '')
        js = js.replace(var, st)
        js = js.replace("['%s']" % st.strip("'"), '.%s' % st.strip("'"))
    js = js.replace('window.href', 'somefunction')
    js = js.replace('location.assign', 'tempfunction=')
    js = js.replace('location.href', 'tempfunction=')
    js = js.replace('location.replace', 'tempfunction=')
    js = js.replace('location', 'tempfunction=')
    js = js.replace('tempfunction==', 'tempfunction=')
    js = js.replace('for', 'forr')
    js = js.replace('do', 'dodo')
    js = js.replace('if', 'ifif')
    js = js.replace('ifif(name', 'if(name')
    js = js.replace('ifif(caller', 'if(caller')
    js = js.replace('in', 'inin')
    js = js.replace('trining', 'tring')
    return js
