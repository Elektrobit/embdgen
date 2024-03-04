import typing
import sys
from pathlib import Path
from sphinx.util import logging
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.ext.autodoc.importer import import_module
from sphinx.util.nodes import nested_parse_with_titles
from docutils import nodes  # type: ignore
from docutils.statemachine import StringList  # type: ignore

from embdgen.core.utils.class_factory import FactoryBase, Meta  # type: ignore

logger = logging.getLogger(__name__)


class embdgen_config:
    pass

    @classmethod
    def visit(cls):
        pass

    @classmethod
    def depart(cls):
        pass


class EmbdgenConfigDirective(SphinxDirective):
    has_content = True

    def run(self):
        factory: FactoryBase = getattr(import_module(self.content[0]), "Factory")()
        content = StringList()
        for entry_type, cls in factory.class_map().items():
            module = sys.modules[cls.__module__]
            path = Path(module.__file__)
            print(path)
            while path.name != "plugins" and path.parent.name != "embdgen":
                path = path.parent
            path = path.parent.parent
            if path.name == "src":
                path = path.parent
            plugin_name = path.name
            print(plugin_name)
            doc = (cls.__doc__ or entry_type).splitlines()

            title = f"{doc[0]} (``{entry_type}``)"
            content.append(title, "")
            content.append("+" * len(title), "")

            if doc:
                for line in doc[1:]:
                    content.append(line.strip(), "")
                content.append("", "")

            content.append("Options", "")
            content.append("^" * len("Options"), "")
            for key, meta in sorted(
                Meta.get(cls).items(), key=lambda x: (x[1].optional, x[0])
            ):
                org_type = typing.get_origin(meta.typecls)
                if org_type:  # Currently only list is supported, so assume -> list
                    args = typing.get_args(meta.typecls)
                    typename = f"{meta.typecls.__name__}[{args[0].__name__}]"
                else:
                    typename = meta.typecls.__name__

                content.append(
                    ("" if meta.optional else "(required) ")
                    + f"``{key}`` : {typename}",
                    "",
                )
                if not meta.doc:
                    content.append("    N/A", "")
                else:
                    for line in meta.doc.splitlines():
                        content.append(f"    {line.strip()}", "")
            content.append("", "")
        node = nodes.section()
        node.document = self.state.document

        logger.debug("[config] output:\n%s", "\n".join(content))

        nested_parse_with_titles(self.state, content, node)

        return node.children


def setup(app: Sphinx):

    #    app.add_node(embdgen_config)
    #    ,
    #                html=(embdgen_config.visit, embdgen_config.depart),
    #                 latex=(embdgen_config.visit, embdgen_config.depart),
    #                 text=(embdgen_config.visit, embdgen_config.depart))
    app.add_directive("embdgen-config", EmbdgenConfigDirective)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
