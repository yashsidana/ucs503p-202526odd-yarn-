import { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [code, setCode] = useState('');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await axios.post('http://127.0.0.1:8000/analyze', {
        code: code,
      });

      if (response.data.error) {
        setError(response.data.error);
      } else {
        setResult(response.data);
      }
    } catch (err) {
      setError('Failed to connect to the analysis server. Is it running?');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header>
        <h1>Code Clarified: AI Summarizer & Flowchart Generator</h1>
        <p>Paste your Python code below to get a summary and a visual flowchart.</p>
      </header>

      <main>
        <div className="input-panel">
          <form onSubmit={handleSubmit}>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Enter your Python code here..."
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading}>
              {isLoading ? 'Analyzing...' : 'Generate Analysis'}
            </button>
          </form>
        </div>

        <div className="output-panel">
          {isLoading && <div className="loader"></div>}
          {error && <div className="error-message"><strong>Error:</strong> {error}</div>}
          {result && (
            <div className="results">
              <div className="summary-section">
                <h2>AI Summary</h2>
                <pre>{result.summary}</pre>
              </div>
              <div className="flowchart-section">
                <h2>Flowchart</h2>
                <img
                  src={`data:image/png;base64,${result.flowchart_base64}`}
                  alt="Generated Code Flowchart"
                />
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;