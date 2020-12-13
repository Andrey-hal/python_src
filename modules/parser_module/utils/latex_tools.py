
LaTex_syntax = {'subscript':'_{{{}}}','superscript':'^{{{}}}'}

def align_converter(data):
    done=''
    for part in data:
        if part['type'] in LaTex_syntax:
            done+=LaTex_syntax[part['type']].format(part['text'])
        elif part['type'] == 'default':
            done+=part['text']
    return done