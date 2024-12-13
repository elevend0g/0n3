# 0n3: Multi-Model Chat Interface

A powerful full-stack application for unified communication with multiple language models. 0n3 (pronounced "one") serves as a singular interface to interact with diverse AI models simultaneously, enabling seamless code execution and real-time streaming responses.

## Features

- Connect to multiple LLM endpoints simultaneously (OpenAI, OpenRouter, etc.)
- Execute Python code blocks from model responses
- Stream responses in real-time
- Configurable model endpoints through UI
- Markdown and code syntax highlighting
- Environment-based configuration
- Automatic API compatibility handling

## Project Structure

```
0n3/
├── backend/
│   ├── main.py        # FastAPI backend server
│   └── .env           # Backend environment configuration
└── frontend/
    ├── src/
    │   └── components/
    │       └── chat-ui.tsx  # Main chat interface
    ├── package.json
    └── vite.config.ts
```

## Setup

### Backend Setup

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your API keys and endpoints

4. Start the backend server:
   ```bash
   cd backend
   python main.py
   ```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173`

## API Compatibility

The application supports multiple API providers with different requirements:

### OpenAI API
- Message names must match the pattern: `^[a-zA-Z0-9_-]{1,64}$`
- Only alphanumeric characters, underscores, and hyphens are allowed
- Maximum name length is 64 characters
- The backend automatically sanitizes names to meet these requirements

### OpenRouter API
- More flexible name formatting
- Supports spaces and special characters
- No specific length restrictions
- Names are passed through without modification

### Code Output Handling
- Code execution outputs are automatically formatted to be compatible with both APIs
- Output names are sanitized with underscores replacing spaces
- Example: "Model A Code Output" becomes "Model_A_Code_Output" for OpenAI

## Usage

1. Open the application in your browser at `http://localhost:5173`
2. Configure model endpoints in the settings panel (gear icon):
   - For OpenRouter:
     ```
     Name: Model A
     Base URL: https://openrouter.ai/api/v1
     Model ID: anthropic/claude-3.5-sonnet
     ```
   - For OpenAI:
     ```
     Name: Model B
     Base URL: https://api.openai.com/v1
     Model ID: gpt-4
     ```
3. Start chatting with the models
4. Use code blocks with `RUN-CODE` syntax for Python code execution:
   ```python
   RUN-CODE
   ```python
   print("Hello, World!")
   ```
   ```

## API Endpoints

- `POST /chat`: Send messages to multiple LLM endpoints
- `POST /execute-code`: Execute Python code
- `GET /health`: Check backend health and configuration

## Environment Variables

### Backend (.env)

```
ALLOWED_ORIGINS=http://localhost:5173
MODEL_A_API_KEY=your_openrouter_api_key_here
MODEL_B_API_KEY=your_openai_api_key_here
MODEL_A_BASE_URL=https://openrouter.ai/api/v1
MODEL_B_BASE_URL=https://api.openai.com/v1
PORT=8000
```

## Development

### Running Tests

Backend:
```bash
pytest
```

Frontend:
```bash
npm run test
```

### Building for Production

Frontend:
```bash
npm run build
```

Backend:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Security Considerations

- The backend includes code execution capabilities. In production, ensure proper sandboxing and security measures.
- API keys are handled through environment variables. Never commit sensitive credentials.
- CORS is configured for development. Update for production use.
- Message names are automatically sanitized for API compatibility.

## License

MIT License
