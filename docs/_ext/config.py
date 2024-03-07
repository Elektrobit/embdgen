# SPDX-License-Identifier: GPL-3.0-only

import itertools
import sys

import typing
from typing import List, Sequence, Type, Union

from pathlib import Path
from sphinx.util import logging
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.ext.autodoc.importer import import_module
from sphinx.util.nodes import nested_parse_with_titles
from docutils import nodes
from docutils.statemachine import StringList
from docutils.parsers.rst import directives

from embdgen.core.utils.class_factory import FactoryBase, Meta

logger = logging.getLogger(__name__)

class embdgen_config():
    pass

    @classmethod
    def visit(cls):
        pass
    @classmethod
    def depart(cls):
        pass

class EmbdgenConfigDirective(SphinxDirective):
    has_content = True

    required_arguments = 1
    option_spec = {
        'anchor': directives.unchanged
    }

    def _get_real_type(self, typ):
        org_type = typing.get_origin(typ)
        if org_type == Union: # A union is currently only allowed to be TYPE|None i.e. Optional[TYPE]
            args = typing.get_args(typ)
            if len(args) != 2 or args[1] != type(None):
                raise Exception(f"Expected only union with TYPE | None, not {args}")
            return args[0]
        elif org_type == list: 
            return typing.get_args(typ)[0]
        else:
            return typ

    def _collect_utilities(self, classes: Sequence[Type]) -> List[Type]:
        utility_classes = set()
        classes = list(classes)
        while classes:
            cls = classes.pop()
            for meta in Meta.get(cls).values():
                org_type = self._get_real_type(meta.typecls)
                if org_type not in utility_classes and Meta.has_meta(org_type) and org_type.__module__ == cls.__module__:
                    utility_classes.add(org_type)
                    classes.append(org_type)
        return sorted(utility_classes, key = lambda x: x.__name__)

    def run(self):
        anchor = self.options.get('anchor', None)
        factory: FactoryBase = getattr(import_module(self.arguments[0]), 'Factory')()
        content = StringList()
        for entry_type, cls in itertools.chain(factory.class_map().items(), [("", v) for v in self._collect_utilities(factory.class_map().values())]):
            module = sys.modules[cls.__module__]
            path = Path(module.__file__)
            while path.name != "plugins" and path.parent.name != "embdgen":
                path = path.parent
            path = path.parent.parent
            if path.name == "src":
                path = path.parent
            doc = (cls.__doc__ or entry_type).splitlines()

            title = doc[0]
            if entry_type:
                title = f"{doc[0]} (``{entry_type}``)"
            else:
                title = f"*Utility:* {doc[0]} ({cls.__name__})"
            if anchor:
                content.append(f".. _{anchor}-{entry_type}:", "")
                content.append("", "")
            content.append(title, "")
            content.append("+" * len(title), "")

            if doc:
                for line in doc[1:]:
                    content.append(line.strip(), "")
                content.append("", "")

            content.append("Options", "")
            content.append("^" * len("Options"), "")
            
            for key, meta in sorted(Meta.get(cls).items(), key = lambda x: (x[1].optional, x[0])):
                org_type = typing.get_origin(meta.typecls)
                if org_type == typing.Union: # A union is currently only allowed to be TYPE|None i.e. Optional[TYPE]
                    args = typing.get_args(meta.typecls)
                    if len(args) != 2 or args[1] != type(None):
                        raise Exception(f"Expected only union with TYPE | None, not {args}")
                    realtype = typing.get_args(meta.typecls)[0]
                    typename = realtype.__name__
                elif org_type == list: 
                    realtype = typing.get_args(meta.typecls)[0]
                    typename = f"{meta.typecls.__name__}[{realtype.__name__}]"
                else:
                    realtype = meta.typecls
                    typename = meta.typecls.__name__
                
                content.append(("" if meta.optional else "(required) ") + f"``{key}`` : {typename}", "")
                if not meta.doc:
                    content.append("    N/A", "")
                else:
                    for line in meta.doc.splitlines():
                        content.append(f"    {line.strip()}", "")
            content.append("", "")
        node = nodes.section()
        node.document = self.state.document

        logger.debug('[config] output:\n%s', '\n'.join(content))

        nested_parse_with_titles(self.state, content, node)

        return node.children

def setup(app: Sphinx):

#    app.add_node(embdgen_config)
#    ,
#                html=(embdgen_config.visit, embdgen_config.depart),
#                 latex=(embdgen_config.visit, embdgen_config.depart),
#                 text=(embdgen_config.visit, embdgen_config.depart))
    app.add_directive('embdgen-config', EmbdgenConfigDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
