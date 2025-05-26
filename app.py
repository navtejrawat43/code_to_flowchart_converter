from flask import Flask, request, render_template, send_file
import ast
import os
from graphviz import Digraph
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = "static"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Utility to generate unique filenames
def unique_filename(ext):
    return f"{uuid.uuid4().hex}.{ext}"

# Function to build flowchart from AST node
def build_flowchart(node, graph, parent=None):
    if isinstance(node, ast.Module):
        for stmt in node.body:
            build_flowchart(stmt, graph, parent)
    elif isinstance(node, ast.FunctionDef):
        func_id = str(uuid.uuid4())
        graph.node(func_id, f"Function: {node.name}")
        if parent:
            graph.edge(parent, func_id)
        for stmt in node.body:
            build_flowchart(stmt, graph, func_id)
    elif isinstance(node, ast.If):
        if_id = str(uuid.uuid4())
        graph.node(if_id, f"If: {ast.unparse(node.test)}")
        if parent:
            graph.edge(parent, if_id)
        for stmt in node.body:
            build_flowchart(stmt, graph, if_id)
        if node.orelse:
            else_id = str(uuid.uuid4())
            graph.node(else_id, "Else")
            graph.edge(if_id, else_id)
            for stmt in node.orelse:
                build_flowchart(stmt, graph, else_id)
    elif isinstance(node, ast.While):
        while_id = str(uuid.uuid4())
        graph.node(while_id, f"While: {ast.unparse(node.test)}")
        if parent:
            graph.edge(parent, while_id)
        for stmt in node.body:
            build_flowchart(stmt, graph, while_id)
    elif isinstance(node, ast.For):
        for_id = str(uuid.uuid4())
        graph.node(for_id, f"For: {ast.unparse(node.target)} in {ast.unparse(node.iter)}")
        if parent:
            graph.edge(parent, for_id)
        for stmt in node.body:
            build_flowchart(stmt, graph, for_id)
    elif isinstance(node, ast.Try):
        try_id = str(uuid.uuid4())
        graph.node(try_id, "Try")
        if parent:
            graph.edge(parent, try_id)
        for stmt in node.body:
            build_flowchart(stmt, graph, try_id)
        for handler in node.handlers:
            except_id = str(uuid.uuid4())
            graph.node(except_id, f"Except: {handler.type.id if handler.type else 'Exception'}")
            graph.edge(try_id, except_id)
            for stmt in handler.body:
                build_flowchart(stmt, graph, except_id)
    elif isinstance(node, ast.Break):
        break_id = str(uuid.uuid4())
        graph.node(break_id, "Break")
        if parent:
            graph.edge(parent, break_id)
    elif isinstance(node, ast.Continue):
        cont_id = str(uuid.uuid4())
        graph.node(cont_id, "Continue")
        if parent:
            graph.edge(parent, cont_id)
    elif isinstance(node, ast.Expr):
        expr_id = str(uuid.uuid4())
        graph.node(expr_id, f"Expr: {ast.unparse(node)}")
        if parent:
            graph.edge(parent, expr_id)
    elif isinstance(node, ast.Assign):
        assign_id = str(uuid.uuid4())
        graph.node(assign_id, f"Assign: {ast.unparse(node)}")
        if parent:
            graph.edge(parent, assign_id)

# AST Tree Generator
def build_ast_tree(node, graph, parent=None):
    node_id = str(uuid.uuid4())
    label = type(node).__name__
    graph.node(node_id, label)
    if parent:
        graph.edge(parent, node_id)
    for field, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            build_ast_tree(value, graph, node_id)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    build_ast_tree(item, graph, node_id)

@app.route("/", methods=["GET", "POST"])
def index():
    image_url = None
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        fmt = request.form.get("format", "").strip()

        # Debug: print input received
        print("Code received:", code)
        print("Format received:", fmt)

        if not code:
            return "Code is missing.", 400
        if not fmt:
            return "Format is missing.", 400

        # Parse code to AST
        try:
            tree = ast.parse(code)
        except Exception as e:
            return f"Error parsing code: {str(e)}", 400

        # Generate flowchart
        flowchart = Digraph(format=fmt)
        build_flowchart(tree, flowchart)
        flow_filename = unique_filename(fmt)
        flowchart.render(filename=flow_filename, directory=UPLOAD_FOLDER, cleanup=True)

        # Generate AST diagram
        ast_graph = Digraph(format=fmt)
        build_ast_tree(tree, ast_graph)
        ast_filename = unique_filename(fmt)
        ast_graph.render(filename=ast_filename, directory=UPLOAD_FOLDER, cleanup=True)

        return render_template("index.html", flowchart_url=f"/static/{flow_filename}", ast_url=f"/static/{ast_filename}", selected_format=fmt)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
