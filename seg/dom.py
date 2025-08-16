# pip install networkx
import networkx as nx
from html import escape
from itertools import count

class NXDOM:
    def __init__(self, root_tag="html", **attrs):
        self.g = nx.DiGraph()
        self._nid = count()
        self._edge_order = count()
        self.root = self._new_node(root_tag, **attrs)

    # ---- node/edge helpers ----
    def _new_node(self, tag, text=None, **attrs):
        nid = next(self._nid)
        classes = attrs.pop("class_", None) or attrs.pop("class", "")
        if isinstance(classes, (list, tuple, set)):
            classes = " ".join(classes)
        data = {
            "tag": tag,
            "attrs": dict(attrs),
            "text": text or "",
        }
        if classes:
            data["attrs"]["class"] = classes
        self.g.add_node(nid, **data)
        return nid

    def append(self, parent, tag=None, text=None, **attrs):
        """Append an element node or an existing node id to parent."""
        if isinstance(tag, int):  # existing node id
            child = tag
        else:
            child = self._new_node(tag, text=text, **attrs)
        self.g.add_edge(parent, child, order=next(self._edge_order))
        return child

    def set_attr(self, node, **attrs):
        self.g.nodes[node]["attrs"].update(attrs)

    def set_text(self, node, text):
        self.g.nodes[node]["text"] = text

    # ---- querying (very small subset) ----
    def query(self, selector):
        """
        Supported:
          - tag (e.g., 'div')
          - #id
          - .class
          - [attr=value]
        Combined like 'div.card', 'a.button.primary'
        No combinators (descendant/child) to keep it simple.
        """
        parts = []
        buf = ""
        i = 0
        while i < len(selector):
            c = selector[i]
            if c in ".#[":
                if buf:
                    parts.append(("tag", buf))
                    buf = ""
                if c == ".":
                    j = i + 1
                    while j < len(selector) and selector[j] not in ".#[":
                        j += 1
                    parts.append(("class", selector[i+1:j]))
                    i = j
                    continue
                if c == "#":
                    j = i + 1
                    while j < len(selector) and selector[j] not in ".#[":
                        j += 1
                    parts.append(("id", selector[i+1:j]))
                    i = j
                    continue
                if c == "[":
                    j = selector.index("]", i)
                    kv = selector[i+1:j]
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        v = v.strip('"\'')
                        parts.append(("attr_eq", (k.strip(), v)))
                    else:
                        parts.append(("attr_has", kv.strip()))
                    i = j + 1
                    continue
            else:
                buf += c
                i += 1
        if buf:
            parts.append(("tag", buf))

        def match(n):
            d = self.g.nodes[n]
            tag = d["tag"]
            attrs = d["attrs"]
            for t, val in parts:
                if t == "tag" and val and tag != val:
                    return False
                if t == "id" and attrs.get("id") != val:
                    return False
                if t == "class":
                    if "class" not in attrs or val not in attrs["class"].split():
                        return False
                if t == "attr_eq":
                    k, v = val
                    if attrs.get(k) != v:
                        return False
                if t == "attr_has":
                    if val not in attrs:
                        return False
            return True

        return [n for n in self.g.nodes if match(n)]

    # ---- HTML serialization ----
    def _children(self, n):
        # Return children sorted by insertion order
        return sorted(self.g.successors(n), key=lambda c: self.g.edges[n, c]["order"])

    def _attrs_to_str(self, attrs):
        if not attrs:
            return ""
        parts = []
        for k, v in attrs.items():
            parts.append(f'{k}="{escape(str(v), quote=True)}"')
        return " " + " ".join(parts)

    def to_html(self, node=None):
        if node is None:
            node = self.root
        nd = self.g.nodes[node]
        tag = nd["tag"]
        attrs = self._attrs_to_str(nd["attrs"])
        text = escape(nd["text"])
        children = self._children(node)

        # Simple void elements handling (extend as needed)
        void = {"br", "hr", "img", "meta", "link", "input"}
        if tag in void:
            return f"<{tag}{attrs}>"

        inner = []
        if text:
            inner.append(text)
        for ch in children:
            inner.append(self.to_html(ch))
        return f"<{tag}{attrs}>" + "".join(inner) + f"</{tag}>"

    # ---- pretty print (tree view) ----
    def pretty(self, node=None, depth=0):
        if node is None:
            node = self.root
        nd = self.g.nodes[node]
        attrs = " ".join(
            [f'{k}="{v}"' for k, v in nd["attrs"].items()]
        )
        lead = "  " * depth
        line = f"{lead}<{nd['tag']}" + (f" {attrs}" if attrs else "") + ">"
        if nd["text"]:
            line += f" {nd['text']!r}"
        print(line)
        for ch in self._children(node):
            self.pretty(ch, depth + 1)

if __name__ == "__main__":
        
    # ----------------- Example usage -----------------
    dom = NXDOM("html", lang="en")
    head = dom.append(dom.root, "head")
    dom.append(head, "meta", charset="utf-8")
    dom.append(head, "title", text="NetworkX DOM")

    body = dom.append(dom.root, "body")
    app = dom.append(body, "div", id="app", class_=["container", "p-4"])
    dom.append(app, "h1", text="Hello, DOM (via NetworkX)")
    p = dom.append(app, "p")
    dom.append(p, "strong", text="Tip: ")
    dom.append(p, "span", text="Use graphs for trees too!")

    # Query examples
    print("By id:", dom.query("#app"))
    print("By class:", dom.query(".container"))
    print("By tag:", dom.query("p"))

    # Tree view
    dom.pretty()

    # HTML string
    html_str = dom.to_html()
    print("\n--- HTML ---\n", html_str)
