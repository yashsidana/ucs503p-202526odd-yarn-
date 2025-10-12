import ast
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import graphviz
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. Configuration ---
# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure the Gemini API
try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # Initialize the generative model
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    model = None


# --- 2. LLM-Powered Code Summarization Logic ---
def summarize_code_with_llm(code: str) -> str:
    """Generates a natural language summary using the Gemini LLM."""
    if not model:
        return "LLM model is not configured. Please check your API key."

    # A well-defined prompt for the LLM
    prompt = f"""
    You are an expert code analyst. Analyze the following Python code and provide a concise, single-paragraph summary in plain English.
    Explain the overall purpose of the code, what the main functions do, and what the expected outcome is.
    Do not describe the code line-by-line. Focus on the high-level logic.

    --- CODE ---
    {code}
    --- END CODE ---
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Could not generate summary from LLM: {e}"


# --- 3. Flowchart Generation Logic (Unchanged) ---
def generate_flowchart(tree):
    """Generates a flowchart in Graphviz DOT format from the AST."""
    dot = graphviz.Digraph('CodeFlow', comment='Control Flow Graph')
    dot.attr('node', shape='box', style='rounded')
    dot.attr(rankdir='TB', newrank='true')

    node_counter = 0

    def get_node_id(label):
        nonlocal node_counter
        node_id = f'node{node_counter}'
        # Sanitize label for DOT format
        sanitized_label = label.replace('"', '\\"').replace('\n', '\\n')
        dot.node(node_id, sanitized_label)
        node_counter += 1
        return node_id

    start_node = get_node_id("Start")
    end_node = get_node_id("End")
    current_node = start_node

    # Simple traversal for prototype (can be expanded)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_node = get_node_id(f"Define Function: {node.name}()")
            dot.edge(current_node, func_node)
            current_node = func_node
        elif isinstance(node, ast.If):
            # For if-else statements
            condition_text = ast.unparse(node.test)
            cond_node = get_node_id(f"Condition: {condition_text}")
            dot.edge(current_node, cond_node)
            
            # Placeholder for TRUE branch
            true_branch_end = get_node_id("Process TRUE branch")
            dot.edge(cond_node, true_branch_end, label='True')
            
            # Placeholder for FALSE branch
            if node.orelse:
                false_branch_end = get_node_id("Process FALSE branch")
                dot.edge(cond_node, false_branch_end, label='False')

    dot.edge(current_node, end_node)
    return dot.source


# --- 4. API Endpoint ---
@app.route('/process_code', methods=['POST'])
def process_code():
    """API endpoint to receive code, summarize it, and generate a flowchart."""
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({"error": "No code provided"}), 400

    code = data['code']

    try:
        # First, validate the code syntax by trying to parse it
        tree = ast.parse(code)

        # Generate the summary using the LLM
        summary = summarize_code_with_llm(code)

        # Generate the flowchart from the AST
        flowchart_dot = generate_flowchart(tree)

        return jsonify({
            "summary": summary,
            "flowchart_dot": flowchart_dot
        })

    except SyntaxError as e:
        return jsonify({"error": f"Invalid Python syntax: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)