from pygments.lexer import RegexLexer, bygroups, inherit, using
from pygments.lexers.shell import BashLexer
from pygments.token import Comment, Keyword, Literal, Name, Punctuation, String, Text


class EcflowDefLexer(RegexLexer):
    name = "ecFlow Definition"
    aliases = ["ecflowdef"]
    filenames = ["*.def"]

    tokens = {
        "root": [
            (r"#.*?\n", Comment),
            (
                r"(^\s*(?:suite|family|task))(\s+(?:[A-Za-z0-9_][A-Za-z0-9_\.]*))",
                bygroups(Keyword, Name),
            ),
            (r"^\s*(?:endsuite|endfamily)", Keyword),
            (
                r"^(\s*(?:edit|label|event|limit|inlimit|meter))(\s+-[a-z])?(\s+(?:[A-Za-z0-9_][A-Za-z0-9_\.]*))(\s(?:.*?))",  # noqa: E501
                bygroups(Keyword, String, Name.Variable, String),
            ),
            (
                r"(^\s*(?:complete|late|trigger|time|cron|date|day|autoarchive|autorestore))(\s+(?:.*))(\s*#.*?\n)",
                bygroups(Keyword, String, Comment),
            ),
            (
                r"(^\s*(?:complete|late|trigger|time|cron|date|day|autoarchive|autorestore))(\s+(?:.*))",
                bygroups(Keyword, String),
            ),
            (
                r"(defstatus)(\s+(?:aborted|active|complete|queued))",
                bygroups(Keyword, Name.Constant),
            ),
            (
                r"(repeat)(\s+(?:date(?:list)?|day|month|year|integer|enumerated|string))(\s+(?:.+?))(\s(?:.*))",
                bygroups(Keyword, Name.Other, Name.Variable, Literal.Date),
            ),
            # Required
            (r"(?s)\$?\"(\\.|[^\"\$])*\"", String.Double),
            (r"\s", Text),
            (r"[^=\s\[\]{}()$\"'`\<&|;]+", Text),
        ],
    }


class EcflowShellLexer(BashLexer):
    name = "ecFlow Shell Script"
    aliases = ["ecflowshell"]
    filenames = ["*.ecf"]

    tokens = {
        "root": [
            (
                r"(?s)(^%manual$)(.*?)?(^%end$)",
                bygroups(Keyword, Comment.Multiline, Keyword),
            ),
            (
                r"(?s)(^%comment$)(.*?)?(^%end$)",
                bygroups(Keyword, Comment.Multiline, Keyword),
            ),
            (
                r"(?s)(^%nopp$)(.*?)?(^%end$)",
                bygroups(Keyword, using(BashLexer), Keyword),
            ),
            (
                r"(^%include(?:nopp|once)?)(\s+)(<)(.*)(>)$",
                bygroups(Keyword, Text, Punctuation, Literal, Punctuation),
            ),
            (
                r"(%(?!comment|end|include|manual|nopp).*?)(:.*?)?(%)",
                bygroups(Name.Variable, String, Name.Variable),
            ),
            # Required
            inherit,
        ]
    }


def setup(app):
    app.add_lexer("ecflow_def", EcflowDefLexer)
    app.add_lexer("ecflow_shell", EcflowShellLexer)
