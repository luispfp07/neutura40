#!/usr/bin/env python3
"""
NEUTURA - GERADOR DAS PÁGINAS PT E EN

As páginas são editadas em src/*.html, onde cada texto existe nas duas línguas:
    <span class="lang-pt">Receitas</span><span class="lang-en">Recipes</span>
e alguns atributos têm a versão inglesa à parte (data-alt-en, data-aria-en,
data-en nas <option>, data-title-en no <html>, data-description-en na meta).

Este script gera:
    ./<pagina>.html      versão portuguesa (URL principal)
    ./en/<page>.html     versão inglesa, com URL próprio
    ./sitemap.xml        com as duas versões ligadas por hreflang

Uso:  python3 build.py
Não editar diretamente os .html gerados: as alterações perdem-se no próximo build.
"""
import html
import os
import re
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
DOMAIN = "https://www.neutura.pt/"

# Página PT -> página EN (as que não estão aqui só existem em PT)
PAGES = {
    "index.html": "index.html",
    "marca.html": "brand.html",
    "receitas.html": "recipes.html",
    "receita.html": "rustic-migas-recipe.html",
    "b2b.html": "b2b.html",
    "carreiras.html": "careers.html",
    "contactos.html": "contacts.html",
    "privacidade.html": "privacy.html",
    "termos.html": "terms.html",
    "cookies.html": "cookies.html",
}
NOINDEX = {"404.html"}

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
URL_ATTRS = {"href", "src", "srcset", "data-src", "poster"}
EN_ONLY_ATTRS = {"data-alt-en", "data-aria-en", "data-en", "data-title-en", "data-description-en", "data-keep-url"}


def url(pt_name, lang):
    """URL absoluto de uma página."""
    if lang == "pt":
        return DOMAIN + ("" if pt_name == "index.html" else pt_name)
    en = PAGES[pt_name]
    return DOMAIN + "en/" + ("" if en == "index.html" else en)


def rewrite_url(value, lang):
    """Na versão EN, os links para páginas passam para a versão EN e os recursos ganham '../'."""
    if lang == "pt" or not value or re.match(r"^(https?:|mailto:|tel:|#|/|data:)", value):
        return value
    if " " in value.strip() and "," in value:  # srcset com vários candidatos
        return ", ".join(rewrite_url(part.strip(), lang) for part in value.split(","))
    path, sep, frag = value.partition("#")
    if path in PAGES:
        return PAGES[path] + sep + frag
    return "../" + value


class LangFilter(HTMLParser):
    """Mantém só a língua pedida e reescreve atributos e URLs."""

    def __init__(self, lang):
        super().__init__(convert_charrefs=False)
        self.lang = lang
        self.keep_cls = "lang-" + lang
        self.drop_cls = "lang-en" if lang == "pt" else "lang-pt"
        self.out = []
        self.stack = []          # (tag, acção) para cada elemento aberto
        self.replace_text = None  # texto que substitui o conteúdo do elemento atual

    @property
    def dropping(self):
        return any(action in ("drop", "replace") for _, action in self.stack)

    def emit(self, text):
        if not self.dropping:
            self.out.append(text)

    def handle_decl(self, decl):
        self.emit("<!" + decl + ">")

    def handle_comment(self, data):
        self.emit("<!--" + data + "-->")

    def handle_data(self, data):
        self.emit(data)

    def handle_entityref(self, name):
        self.emit("&" + name + ";")

    def handle_charref(self, name):
        self.emit("&#" + name + ";")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, self_closing=True)

    def handle_starttag(self, tag, attrs, self_closing=False):
        raw = self.get_starttag_text()
        is_void = tag in VOID or self_closing
        if self.dropping:
            if not is_void:
                self.stack.append((tag, "drop"))
            return

        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "body":
            classes = []  # <body class="lang-pt"> é só um marcador da fonte
        if self.drop_cls in classes:
            if not is_void:
                self.stack.append((tag, "drop"))
            return
        if classes == [self.keep_cls] and tag in ("span", "div"):
            self.stack.append((tag, "unwrap"))
            return

        changed = False
        new = []
        replace = None
        for k, v in attrs:
            if k in EN_ONLY_ATTRS:
                changed = True
                continue
            if k == "class" and self.keep_cls in classes:
                v = " ".join(c for c in classes if c != self.keep_cls)
                changed = True
            if k in URL_ATTRS and v is not None and "data-keep-url" not in a:
                nv = rewrite_url(v, self.lang)
                changed |= nv != v
                v = nv
            if self.lang == "en":
                if k == "alt" and "data-alt-en" in a:
                    v, changed = a["data-alt-en"], True
                elif k == "aria-label" and "data-aria-en" in a:
                    v, changed = a["data-aria-en"], True
                elif k == "content" and "data-description-en" in a:
                    v, changed = a["data-description-en"], True
            if tag == "html" and k == "lang":
                v, changed = ("en" if self.lang == "en" else "pt-PT"), True
            if tag == "body" and k == "class":
                changed = True
                continue
            new.append((k, v))
        if self.lang == "en" and tag == "option" and "data-en" in a:
            replace = a["data-en"]
        if self.lang == "en" and tag == "html" and "data-title-en" in a:
            self.title_en = a["data-title-en"]

        if changed:
            parts = [tag]
            for k, v in new:
                parts.append(k if v is None else '%s="%s"' % (k, html.escape(v, quote=True)))
            raw = "<" + " ".join(parts) + (" />" if self_closing else ">")
        self.out.append(raw)

        if tag == "title" and self.lang == "en" and getattr(self, "title_en", None):
            replace = self.title_en
        if replace is not None:
            self.out.append(html.escape(replace, quote=False))
            self.stack.append((tag, "replace"))
        elif not is_void:
            self.stack.append((tag, "keep"))

    def handle_endtag(self, tag):
        # fecha até ao elemento correspondente (tolerante a HTML imperfeito)
        while self.stack:
            t, action = self.stack.pop()
            if t == tag:
                break
        else:
            return
        if action == "keep" and not self.dropping:
            self.out.append("</%s>" % tag)
        elif action == "replace" and not self.dropping:
            self.out.append("</%s>" % tag)

    def result(self):
        return "".join(self.out)


def seo_block(pt_name, lang, title, desc):
    if pt_name in NOINDEX:
        return '<meta name="robots" content="noindex">'
    own = url(pt_name, lang)
    lines = ['<link rel="canonical" href="%s">' % own]
    if pt_name in PAGES:
        lines += [
            '<link rel="alternate" hreflang="pt-PT" href="%s">' % url(pt_name, "pt"),
            '<link rel="alternate" hreflang="en" href="%s">' % url(pt_name, "en"),
            '<link rel="alternate" hreflang="x-default" href="%s">' % url(pt_name, "pt"),
        ]
    lines += [
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Neutura">',
        '<meta property="og:locale" content="%s">' % ("en_GB" if lang == "en" else "pt_PT"),
        '<meta property="og:locale:alternate" content="%s">' % ("pt_PT" if lang == "en" else "en_GB"),
        '<meta property="og:url" content="%s">' % own,
        '<meta property="og:title" content="%s">' % title,
        '<meta property="og:description" content="%s">' % desc,
        '<meta property="og:image" content="%simg/neutura-partilha-redes-sociais.jpg">' % DOMAIN,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    return "\n    ".join(lines)


def lang_selector(pt_name, lang):
    """Seletor PT | EN com links para a mesma página na outra língua."""
    if pt_name in PAGES:
        en_page = PAGES[pt_name]
        pt_href = pt_name if lang == "pt" else "../" + pt_name
        en_href = "en/" + en_page if lang == "pt" else en_page
    else:
        pt_href = "index.html" if lang == "pt" else "../index.html"
        en_href = "en/index.html" if lang == "pt" else "index.html"

    def link(code, href, label, hreflang, active):
        cur = ' active" aria-current="true' if active else ''
        return ('<a class="lang-btn%s" href="%s" hreflang="%s" lang="%s" data-keep-url>'
                '<span aria-hidden="true">%s</span><span class="sr-only">%s</span></a>'
                % (cur, href, hreflang, hreflang, code, label))

    group = "Idioma" if lang == "pt" else "Language"
    return ('<div class="language-selector" role="group" aria-label="%s">\n'
            '                    %s\n'
            '                    <span class="lang-divider" aria-hidden="true">|</span>\n'
            '                    %s\n'
            '                </div>') % (
        group,
        link("PT", pt_href, "Português", "pt-PT", lang == "pt"),
        link("EN", en_href, "English", "en", lang == "en"))


def build_page(pt_name, lang):
    src = open(os.path.join(SRC, pt_name), encoding="utf-8").read()
    head_title = re.search(r"<title>(.*?)</title>", src).group(1)
    title_en = re.search(r'data-title-en="([^"]*)"', src)
    desc = re.search(r'<meta name="description" content="([^"]*)"', src).group(1)
    desc_en = re.search(r'data-description-en="([^"]*)"', src)
    title = (title_en.group(1) if lang == "en" and title_en else head_title)
    description = (desc_en.group(1) if lang == "en" and desc_en else desc)

    src = src.replace("{{SEO}}", seo_block(pt_name, lang, title, description))
    src = src.replace("{{LANG}}", lang_selector(pt_name, lang))

    parser = LangFilter(lang)
    parser.feed(src)
    parser.close()
    out = parser.result()

    note = "<!-- Gerado por build.py a partir de src/%s. Não editar este ficheiro. -->" % pt_name
    out = out.replace("<!DOCTYPE html>", "<!DOCTYPE html>\n" + note, 1)
    assert "{{" not in out, pt_name
    return out


def main():
    os.makedirs(os.path.join(ROOT, "en"), exist_ok=True)
    built = []
    for pt_name in sorted(os.listdir(SRC)):
        if not pt_name.endswith(".html"):
            continue
        with open(os.path.join(ROOT, pt_name), "w", encoding="utf-8") as f:
            f.write(build_page(pt_name, "pt"))
        built.append(pt_name)
        if pt_name in PAGES:
            en_name = PAGES[pt_name]
            with open(os.path.join(ROOT, "en", en_name), "w", encoding="utf-8") as f:
                f.write(build_page(pt_name, "en"))
            built.append("en/" + en_name)

    # sitemap com as duas línguas
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for pt_name in PAGES:
        for lang in ("pt", "en"):
            rows.append("  <url>")
            rows.append("    <loc>%s</loc>" % url(pt_name, lang))
            rows.append('    <xhtml:link rel="alternate" hreflang="pt-PT" href="%s"/>' % url(pt_name, "pt"))
            rows.append('    <xhtml:link rel="alternate" hreflang="en" href="%s"/>' % url(pt_name, "en"))
            rows.append("  </url>")
    rows.append("</urlset>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")

    print("Gerado: " + ", ".join(built) + ", sitemap.xml")


if __name__ == "__main__":
    main()
