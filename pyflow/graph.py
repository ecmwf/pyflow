import os


class Dot:
    def __init__(self, fullnames=True):
        from graphviz import Digraph

        self._dot = Digraph()
        self._nodes = {}
        self._fullnames = fullnames

    def edge(self, node1, node2):
        self._dot.edge(self.node(node1), self.node(node2))

    def node(self, node):
        full = node.fullname
        name = node.name
        label = full if self._fullnames else name
        if full not in self._nodes:
            self._nodes[full] = "id%d" % (len(self._nodes),)
            self._dot.node(self._nodes[full], label, shape=node.shape)
        return self._nodes[full]

    def save(self, path, view=True):
        if os.path.exists(path):
            os.unlink(path)
        self._dot.render(path, view=view)

    # For jupyter notbeook
    def _repr_svg_(self):
        # pre pygraphviz==0.19 use _repr_svg
        try:
            return self._dot._repr_svg_()
        except AttributeError:
            return self._dot._repr_image_svg_xml()
