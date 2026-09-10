# -*- coding: utf-8 -*-
import io
p = 'tools/v4/apply_link_reviews.py'
src = io.open(p, encoding='utf-8').read()
out = []
i = 0
in_str = False
while i < len(src):
    ch = src[i]
    if ch == '"':
        if not in_str:
            in_str = True
            out.append(ch)
        else:
            j = i + 1
            while j < len(src) and src[j] in ' \t':
                j += 1
            nxt = src[j] if j < len(src) else ''
            if nxt in ',)]\n' or nxt == '':
                in_str = False
                out.append(ch)
            else:
                out.append('\u201c' if (out and out[-1] != '\u201d') else '\u201d')
    else:
        out.append(ch)
    i += 1
new = ''.join(out)
io.open(p, 'w', encoding='utf-8', newline='\n').write(new)
print('done, bytes:', len(new.encode('utf-8')))
