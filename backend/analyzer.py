# backend/analyzer.py

import ast
import os
from io import BytesIO
import dotenv
# --- Third-party libraries ---
try:
    import networkx as nx
    from graphviz import Digraph
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
except ImportError as e:
    print(f"Error: A required library is not installed ({e}). Please run:")
    print("pip install networkx graphviz langchain langchain-google-genai")
    exit(1)

# --- AI Summarization ---

# IMPORTANT: Set your Google AI API key here or as an environment variable
 

def generate_ai_summary(code_text: str) -> str:
    """
    Generates a natural language summary of the code's purpose using Google's Gemini model.
    """
   
    if not os.getenv("GOOGLE_API_KEY"):
        return "Error: GOOGLE_API_KEY is not set. Cannot generate AI summary."

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.4)
    prompt_template = """
    You are an expert programmer. Analyze the following Python code and provide a concise, plain-text summary.
    Explain the overall purpose of the code, what each function or class does, and the main logic flow.

    Code:
    ```{code}```

    Summary:
    """
    prompt = PromptTemplate(template=prompt_template, input_variables=["code"])
    chain = LLMChain(llm=llm, prompt=prompt)

    try:
        response = chain.invoke({"code": code_text})
        return response.get('text', 'Failed to get summary from AI response.')
    except Exception as e:
        return f"Could not generate AI summary: {e}"

# --- Code Structure and Flowchart Logic ---

class CodeAnalyzer(ast.NodeVisitor):
    """
    Traverses the AST to extract detailed information for the flowchart.
    """
    def __init__(self):
        self.structure = {"functions": {}}

    def visit_FunctionDef(self, node):
        args = [a.arg for a in node.args.args]
        flow = []
        for body_item in node.body:
            if isinstance(body_item, ast.If):
                condition = ast.unparse(body_item.test)
                flow.append(f"Decision: if {condition}")
            elif isinstance(body_item, ast.For):
                target = ast.unparse(body_item.target)
                iterator = ast.unparse(body_item.iter)
                flow.append(f"Loop: for {target} in {iterator}")
            elif isinstance(body_item, ast.While):
                condition = ast.unparse(body_item.test)
                flow.append(f"Loop: while {condition}")
            elif isinstance(body_item, ast.Return):
                if body_item.value:
                    value = ast.unparse(body_item.value)
                    flow.append(f"Return {value}")
                else:
                    flow.append("Return")
        self.structure["functions"][node.name] = {"args": args, "flow": flow}
        self.generic_visit(node)

def build_graph_model(structure):
    """
    Builds a NetworkX DiGraph model from the extracted code structure.
    """
    G = nx.DiGraph()
    for name, details in structure.get('functions', {}).items():
        subgraph_name = f'cluster_func_{name}'
        func_start_id = f"func_{name}_start"
        G.add_node(func_start_id, label='Start', shape='ellipse', fillcolor='palegreen', subgraph=subgraph_name, func_name=name, func_args=details['args'])
        last_node_id = func_start_id
        flow = details.get('flow', [])
        if not flow:
            empty_node_id = f"func_{name}_empty"
            G.add_node(empty_node_id, label='No operations', shape='plaintext', subgraph=subgraph_name)
            G.add_edge(last_node_id, empty_node_id)
            last_node_id = empty_node_id
        else:
            for i, step in enumerate(flow):
                step_id = f"func_{name}_step_{i}"
                if step.startswith("Decision"):
                    G.add_node(step_id, label=step.replace("Decision: ", ""), shape='diamond', fillcolor='khaki', subgraph=subgraph_name)
                else:
                    G.add_node(step_id, label=step, shape='box', subgraph=subgraph_name)
                G.add_edge(last_node_id, step_id)
                last_node_id = step_id
        func_end_id = f"func_{name}_end"
        G.add_node(func_end_id, label='End', shape='ellipse', fillcolor='lightcoral', subgraph=subgraph_name)
        G.add_edge(last_node_id, func_end_id)
    return G

def create_logic_flowchart(graph):
    """
    Creates a Graphviz flowchart from a NetworkX graph model.
    """
    dot = Digraph('CodeFlow', format='png')
    dot.attr('node', style='rounded,filled', fillcolor='white')
    dot.attr(rankdir='TB', splines='ortho', labelloc='t', label='Code Logic Flowchart')
    dot.attr(fontname="Helvetica")
    subgraph_clusters = {}
    if not graph.nodes:
        dot.node("main", "No functions found to map.")
    for node_id, attrs in graph.nodes(data=True):
        subgraph_name = attrs.get('subgraph')
        if subgraph_name and subgraph_name not in subgraph_clusters:
            if subgraph_name.startswith('cluster_func'):
                cluster = Digraph(subgraph_name)
                func_name = attrs.get('func_name', '')
                func_args = attrs.get('func_args', [])
                cluster.attr(label=f"Function: {func_name}({', '.join(func_args)})", style='rounded')
                subgraph_clusters[subgraph_name] = cluster
        container = subgraph_clusters.get(subgraph_name, dot)
        node_attrs = {k: v for k, v in attrs.items() if k not in ['subgraph', 'func_name', 'func_args']}
        container.node(node_id, **node_attrs)
    for cluster in subgraph_clusters.values():
        dot.subgraph(cluster)
    for u, v in graph.edges():
        dot.edge(u, v)
    return dot