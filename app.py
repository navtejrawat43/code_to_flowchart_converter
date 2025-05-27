from flask import Flask, request, render_template, send_file
import ast, os, uuid, io, tokenize
from graphviz import Digraph
from reportlab.pdfgen import canvas
from PyPDF2 import PdfMerger

app = Flask(__name__)
UPLOAD_FOLDER = "static"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def unique_base():
    return uuid.uuid4().hex

def clean_code(code):
    return code.replace('\u202f', ' ').replace('\xa0', ' ').strip()

def build_flowchart(node, graph, parent=None):
    last_node = parent
    if isinstance(node, ast.Module):
        for stmt in node.body:
            last_node = build_flowchart(stmt, graph, last_node)
    elif isinstance(node, ast.FunctionDef):
        func_id = str(uuid.uuid4())
        graph.node(func_id, f"Function: {node.name}", shape="oval")
        if parent: graph.edge(parent, func_id)
        last = func_id
        for stmt in node.body:
            last = build_flowchart(stmt, graph, last)
        return last
    elif isinstance(node, ast.If):
        if_id = str(uuid.uuid4())
        graph.node(if_id, f"If: {ast.unparse(node.test)}", shape="diamond")
        if parent: graph.edge(parent, if_id)
        if node.body:
            then_last = str(uuid.uuid4())
            graph.node(then_last, "", shape="point")
            graph.edge(if_id, then_last, label="True")
            for stmt in node.body:
                then_last = build_flowchart(stmt, graph, then_last)
        if node.orelse:
            else_last = str(uuid.uuid4())
            graph.node(else_last, "", shape="point")
            graph.edge(if_id, else_last, label="False")
            for stmt in node.orelse:
                else_last = build_flowchart(stmt, graph, else_last)
        return if_id
    elif isinstance(node, ast.While):
        while_id = str(uuid.uuid4())
        graph.node(while_id, f"While: {ast.unparse(node.test)}", shape="diamond")
        if parent: graph.edge(parent, while_id)
        loop_last = while_id
        for stmt in node.body:
            loop_last = build_flowchart(stmt, graph, loop_last)
        graph.edge(loop_last, while_id, label="Loop")  # Loop back to while condition
        exit_point = str(uuid.uuid4())
        graph.node(exit_point, "", shape="point")
        graph.edge(while_id, exit_point, label="False")  # Exit condition
        return exit_point
    elif isinstance(node, ast.Assign):
        aid = str(uuid.uuid4())
        graph.node(aid, f"Assign: {ast.unparse(node)}", shape="box")
        if parent: graph.edge(parent, aid)
        return aid
    elif isinstance(node, ast.Expr):
        eid = str(uuid.uuid4())
        graph.node(eid, f"Expr: {ast.unparse(node)}", shape="box")
        if parent: graph.edge(parent, eid)
        return eid
    elif isinstance(node, ast.Return):
        rid = str(uuid.uuid4())
        graph.node(rid, f"Return: {ast.unparse(node.value)}", shape="box")
        if parent: graph.edge(parent, rid)
        return rid
    return last_node

def build_ast_tree(node, graph, parent=None):
    nid = str(uuid.uuid4())
    graph.node(nid, type(node).__name__)
    if parent: graph.edge(parent, nid)
    for field, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            build_ast_tree(value, graph, nid)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    build_ast_tree(item, graph, nid)

def generate_tokenization(code):
    tokens = []
    reader = io.BytesIO(code.encode('utf-8')).readline
    for tok in tokenize.tokenize(reader):
        if tok.type != tokenize.ENCODING:
            tokens.append(f"{tokenize.tok_name[tok.type]}:\t{tok.string}")
    return "\n".join(tokens)

@app.route("/", methods=["GET", "POST"])
def index():
    code = ""
    selected_view = "all"
    error = ""

    ast_files = {}
    flowchart_files = {}
    token_data = ""
    merged_pdf_url = ""

    if request.method == "POST":
        code = clean_code(request.form.get("code", ""))
        selected_view = request.form.get("view", "all")

        if not code:
            error = "Code is missing."
        else:
            try:
                tree = ast.parse(code)
                base_id = unique_base()

                # Generate SVG flowchart
                flowchart = Digraph(format="svg")
                flowchart.attr(rankdir="TB")
                build_flowchart(tree, flowchart)
                flowchart_path = os.path.join(UPLOAD_FOLDER, f"flowchart_{base_id}")
                flowchart_out = flowchart.render(filename=flowchart_path, cleanup=True)
                flowchart_files["svg"] = f"/static/{os.path.basename(flowchart_out)}"

                # Generate SVG AST
                ast_graph = Digraph(format="svg")
                build_ast_tree(tree, ast_graph)
                ast_path = os.path.join(UPLOAD_FOLDER, f"ast_{base_id}")
                ast_out = ast_graph.render(filename=ast_path, cleanup=True)
                ast_files["svg"] = f"/static/{os.path.basename(ast_out)}"

                # Generate tokenization text
                token_data = generate_tokenization(code)
                token_pdf_path = os.path.join(UPLOAD_FOLDER, f"token_{base_id}.pdf")
                c = canvas.Canvas(token_pdf_path)
                for i, line in enumerate(token_data.splitlines()):
                    c.drawString(30, 800 - i * 15, line)
                c.save()

                # Merge PDFs (AST, Flowchart, Tokens)
                merged_path = os.path.join(UPLOAD_FOLDER, f"merged_{base_id}.pdf")
                merger = PdfMerger()
                for svg_pdf in [ast_path + ".pdf", flowchart_path + ".pdf", token_pdf_path]:
                    if os.path.exists(svg_pdf):
                        merger.append(svg_pdf)
                merger.write(merged_path)
                merger.close()
                merged_pdf_url = "/static/" + os.path.basename(merged_path)

            except Exception as e:
                error = f"Parsing Error: {str(e)}"

    return render_template(
        "index.html",
        code=code,
        selected_view=selected_view,
        ast_files=ast_files,
        flowchart_files=flowchart_files,
        token_data=token_data,
        merged_pdf_url=merged_pdf_url,
        error=error
    )

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

if __name__ == "__main__":
    app.run(debug=True)
