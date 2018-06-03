# -*- encoding: utf-8

import re

import markdown
from markdown.extensions import Extension
from markdown.extensions.smarty import SmartyExtension
from markdown.preprocessors import Preprocessor


def title_markdown(md):
    """Renders a Markdown string as HTML for use in a bookmark title."""
    if len(md.splitlines()) != 1:
        raise ValueError(f"Title must be at most one line; got {md!r}")

    # We don't want titles to render with <h1> or similar tags if they start
    # with a '#', so escape that if necessary.
    if md.startswith('#'):
        md = f'\\{md}'

    res = markdown.markdown(md, extensions=[SmartyExtension()])
    return res.replace('<p>', '').replace('</p>', '')


class AutoLinkPreprocessor(Preprocessor):
    """
    Preprocessor that converts anything that looks like a URL into a link.
    """
    def run(self, lines):
        new_lines = []
        for line in lines:
            for u in re.findall(r'(https?://[^\s]+?)(?:\s|$)', line):
                line = line.replace(u, f'<{u}>')
            new_lines.append(line)
        return new_lines


class BlockquotePreprocessor(Preprocessor):
    """
    Preprocessor that converts ``<blockquote>``s back into Markdown syntax.
    """
    def run(self, lines):
        text = '\n'.join(lines)
        blockquotes = re.findall(r'<blockquote>(?:[^<]+?)</blockquote>', text)
        for bq_html in blockquotes:
            bq_inner = bq_html[len('<blockquote>'):-len('</blockquote>')]
            bq_md_lines = []

            # We need to preserve line breaks in the original Markdown --
            # even if it's a non-standard part of the HTML spec, it's what
            # the Pinboard website does.
            inner_lines = bq_inner.strip().splitlines()
            for i, line in enumerate(inner_lines):
                if i == len(inner_lines) - 1:
                    bq_md_lines.append(f'> {line}')
                else:
                    if inner_lines[i + 1].strip():
                        bq_md_lines.append(f'> {line}  ')
                    else:
                        bq_md_lines.append(f'> {line}')

            bq_md = '\n'.join(bq_md_lines)

            text = text.replace(bq_html, '\n\n' + bq_md + '\n\n')
        return text.splitlines()


class PinboardExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        md.preprocessors.add(
            'unconvert_blockquotes',
            BlockquotePreprocessor(md),
            '>normalize_whitespace'
        )
        md.preprocessors.add(
            'inline_urls',
            AutoLinkPreprocessor(md),
            '>normalize_whitespace'
        )


def description_markdown(md):
    """Renders a Markdown string as HTML for use in a bookmark description."""
    return markdown.markdown(md, extensions=[
        SmartyExtension(),
        PinboardExtension()
    ]).replace('\n</p>', '</p>')
