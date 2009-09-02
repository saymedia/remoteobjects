"""

A Sphinx extension to autodocument __init__ methods.

"""


import logging

def document_init_methods(app, what, name, obj, skip, options):
    if not skip:
        return
    if name != '__init__':
        return
    if not getattr(obj, '__doc__', None):
        return

    # Don't skip it.
    return False

def setup(app):
    app.connect('autodoc-skip-member', document_init_methods)
