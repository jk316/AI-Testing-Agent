"""
AI Test Agent - Flask Web Application
"""

from flask import Flask, request, jsonify, send_from_directory
from backend.agents.orchestrator import OrchestratorAgent

app = Flask(__name__, static_folder='../frontend/static', template_folder='../frontend')

_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorAgent()
    return _orchestrator


@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')


@app.route('/api/execute', methods=['POST'])
def execute():
    """Execute the network test compilation workflow"""
    data = request.get_json()

    if not data or 'input' not in data:
        return jsonify({'error': 'No input provided'}), 400

    nl_input = data.get('input', '').strip()
    if not nl_input:
        return jsonify({'error': 'Input cannot be empty'}), 400

    try:
        orchestrator = get_orchestrator()
        result = orchestrator.execute(nl_input)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e), 'status': 'error'}), 400
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/api/status')
def status():
    """Get workflow status steps"""
    return jsonify({
        'steps': [
            {"id": "planner", "name": "Planner Agent", "description": "NL → DSL"},
            {"id": "compiler", "name": "Compiler Agent", "description": "DSL → hping3"},
            {"id": "verifier", "name": "Verifier Agent", "description": "Semantic Validation"},
        ]
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
