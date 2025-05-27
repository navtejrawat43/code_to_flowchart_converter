import ast
import uuid
import tkinter as tk
from tkinter import scrolledtext, messagebox
from graphviz import Digraph

# ===== Flowchart Builder =====
class FlowchartBuilder(ast.NodeVisitor):
    def __init__(self):
        self.graph = Digraph(comment="Code Flowchart")
        self.prev_node = None
        self.start_node = self._add_node("Start", shape='circle')

    def _add_node(self, label, shape='box'):
        node_id = str(uuid.uuid4())[:8]
        self.graph.node(node_id, label, shape=shape)
        return node_id

    def _connect(self, from_node, to_node, label=''):
        self.graph.edge(from_node, to_node, label=label)

    def visit_FunctionDef(self, node):
        self.prev_node = self.start_node
        for stmt in node.body:
            self.visit(stmt)
        end_node = self._add_node("End", shape='doublecircle')
        self._connect(self.prev_node, end_node)

    def visit_If(self, node):
        cond = ast.unparse(node.test)
        cond_node = self._add_node(f"If {cond}?", shape='diamond')
        self._connect(self.prev_node, cond_node)

        self.prev_node = cond_node
        then_start = self._add_node("Then", shape='circle')
        self._connect(cond_node, then_start, label='True')
        self.prev_node = then_start
        for stmt in node.body:
            self.visit(stmt)
        then_end = self.prev_node

        self.prev_node = cond_node
        else_start = self._add_node("Else", shape='circle')
        self._connect(cond_node, else_start, label='False')
        self.prev_node = else_start
        for stmt in node.orelse:
            self.visit(stmt)
        else_end = self.prev_node

        merge_node = self._add_node("Merge", shape='circle')
        self._connect(then_end, merge_node)
        self._connect(else_end, merge_node)
        self.prev_node = merge_node

    def visit_Expr(self, node):
        expr = ast.unparse(node)
        node_id = self._add_node(expr)
        self._connect(self.prev_node, node_id)
        self.prev_node = node_id

    def visit_Return(self, node):
        expr = ast.unparse(node)
        node_id = self._add_node(f"Return {expr}")
        self._connect(self.prev_node, node_id)
        self.prev_node = node_id

    def visit_While(self, node):
        cond = ast.unparse(node.test)
        cond_node = self._add_node(f"While {cond}?", shape='diamond')
        self._connect(self.prev_node, cond_node)

        self.prev_node = cond_node
        body_start = self._add_node("Loop Start", shape='circle')
        self._connect(cond_node, body_start, label='True')
        self.prev_node = body_start
        for stmt in node.body:
            self.visit(stmt)
        self._connect(self.prev_node, cond_node)

        exit_node = self._add_node("Exit Loop", shape='circle')
        self._connect(cond_node, exit_node, label='False')
        self.prev_node = exit_node

    def visit_For(self, node):
        target = ast.unparse(node.target)
        iter_ = ast.unparse(node.iter)
        cond_node = self._add_node(f"For {target} in {iter_}?", shape='diamond')
        self._connect(self.prev_node, cond_node)

        self.prev_node = cond_node
        body_start = self._add_node("Loop Start", shape='circle')
        self._connect(cond_node, body_start, label='True')
        self.prev_node = body_start
        for stmt in node.body:
            self.visit(stmt)
        self._connect(self.prev_node, cond_node)

        exit_node = self._add_node("Exit Loop", shape='circle')
        self._connect(cond_node, exit_node, label='False')
        self.prev_node = exit_node
# ===== Convert Code to Flowchart Function =====
def code_to_flowchart(code: str, filename="flowchart_output"):
    try:
        tree = ast.parse(code)
        builder = FlowchartBuilder()
        builder.visit(tree)
        builder.graph.render(filename, format='png', view=True)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Parsing failed:\n{e}")
        return False
