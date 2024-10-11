from __future__ import absolute_import

import re


def definition_to_html(d):
    result = []

    for n in d.split("\n"):
        n = re.sub(r'(".*?")', r'<span style="color: red">\1</span>', n)
        n = re.sub(r"('.*?')", r'<span style="color: red">\1</span>', n)

        n = re.sub(
            r"\b([\w:]+)\((.*?)\)",
            r'<span style="font-style: italic;color: blue">\1</span>(\2)',
            n,
        )

        n = re.sub(
            r"^(\s*)(suite|family|task|endsuite|endfamily|defstatus|meter|edit|trigger|complete|aborted|repeat \w+|cron|label|event|limit|inlimit|autocancel|day|date)\b",  # noqa: E501
            r'\1<span style="text-weight: bold; color: green">\2</span>',
            n,
        )

        n = re.sub(
            r" (\%) ",
            r' <span style="text-weight: bold; color: purple">\1</span> ',
            n,
        )

        n = re.sub(
            r"\b(eq|ne|ge|le|gt|lt|and|or|not)\b",
            r'<span style="text-weight: bold; color: purple">\1</span>',
            n,
        )

        n = re.sub(
            r" (complete|aborted|queued|unknown|active|submitted)\b",
            r' <span style="font-style: italic;color: blue">\1</span>',
            n,
        )

        result.append(n)

    return "<pre>%s</pre>" % ("\n".join(result),)


class HTMLWrapper:
    def __init__(self, d):
        self._def = d

    def _repr_html_(self):
        return definition_to_html(self._def)

    __str__ = _repr_html_


def script_to_html(d):
    result = []

    if isinstance(d, str):
        d = d.split("\n")

    for n in d:
        n = re.sub(r"&", r"&amp;", n)
        n = re.sub(r"<", r"&lt;", n)
        n = re.sub(r">", r"&gt;", n)

        s = n.split("#")
        r = ""
        if len(s) > 1:
            n = s[0]
            r = '<span style="font-style: italic;color: blue">#%s</span>' % (
                "".join(s[1:]),
            )

        n = re.sub(r"^(%include.*)$", r'<span style="color: red">\1</span>', n)

        n = re.sub(r"(%.*?%)", r'<span style="color: red">\1</span>', n)

        n = re.sub(
            r"\b(trap|export|echo|wait|set|exit|mkdir|rm|cd)\b",
            r'<span style="text-weight: bold; color: green">\1</span>',
            n,
        )

        result.append(n + r)

    return "<hr><pre>%s</pre><hr>" % ("\n".join(result),)


class FileListHTMLWrapper:
    def __init__(self, d):
        self._def = d

    def _repr_html_(self):
        lines = []
        for name, script in self._content:
            lines.append("<h3>File: %s</h3>" % (name,))
            lines.append(script_to_html(script))
        return "".join(lines)

    __str__ = _repr_html_
