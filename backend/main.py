from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from openai import AsyncOpenAI
import asyncio
import sys
import re
import os
from io import StringIO
import traceback
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

app = FastAPI(title="Multi-Model Chat Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Message(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        # Override dict method to ensure proper serialization
        return {
            "role": self.role,
            "content": self.content,
            "name": self.name
        }

class Endpoint(BaseModel):
    name: str
    apiKey: str
    baseUrl: str
    modelId: str

class ChatRequest(BaseModel):
    messages: List[Message]
    endpoints: List[Endpoint]
    auto_continue: Optional[bool] = False
    max_turns: Optional[int] = 5

class CodeExecution(BaseModel):
    code: str
    timeout: Optional[int] = 30

# Default endpoints with environment variables
DEFAULT_ENDPOINTS = [
    Endpoint(
        name="Model A",
        apiKey=os.getenv("MODEL_A_API_KEY", ""),
        baseUrl=os.getenv("MODEL_A_BASE_URL", "https://api.openai.com/v1"),
        modelId="gpt-3.5-turbo"
    ),
    Endpoint(
        name="Model B",
        apiKey=os.getenv("MODEL_B_API_KEY", ""),
        baseUrl=os.getenv("MODEL_B_BASE_URL", "https://api.openai.com/v1"),
        modelId="gpt-4"
    )
]

def run_code(code: str, timeout: int = 30) -> str:
    """
    Execute Python code in a controlled environment with timeout
    """
    print("\n--- Running code")
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Create a local namespace for execution
        local_ns = {}
        
        # Run code with timeout
        async def run_with_timeout():
            exec(code, local_ns)
        
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait_for(run_with_timeout(), timeout))
        
    except asyncio.TimeoutError:
        return f"Error: Code execution timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing code:\n{traceback.format_exc()}"
    finally:
        sys.stdout = old_stdout
        
    print("--- Finished running code")
    return captured_output.getvalue()

def sanitize_name_for_openai(name: str) -> str:
    """
    Sanitize name field to match OpenAI's requirements:
    - Only alphanumeric characters, underscores, and hyphens
    - Length between 1 and 64 characters
    """
    if not name:
        return None
    # Replace spaces and special chars with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    # Ensure max length of 64
    sanitized = sanitized[:64]
    return sanitized

async def query_llm(endpoint: Endpoint, messages: List[Dict[str, Any]], context: Optional[str] = None) -> str:
    """
    Query an LLM endpoint and return the response with improved error handling
    """
    try:
        # Initialize async client for this endpoint
        client = AsyncOpenAI(
            api_key=endpoint.apiKey,
            base_url=endpoint.baseUrl
        )
        
        # Add context from other models if available
        formatted_messages = []
        if context:
            formatted_messages.append({
                "role": "system",
                "content": f"Context from other models:\n{context}\n\nConsider this context in your response. If you see a question or topic that needs further discussion, provide your perspective and ask a relevant follow-up question."
            })
        
        # Format messages for the API
        for msg in messages:
            formatted_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            # Only include name if it exists and sanitize it for OpenAI endpoints
            if msg.get("name"):
                if "openai.com" in endpoint.baseUrl:
                    sanitized_name = sanitize_name_for_openai(msg["name"])
                    if sanitized_name:
                        formatted_msg["name"] = sanitized_name
                else:
                    formatted_msg["name"] = msg["name"]
            formatted_messages.append(formatted_msg)
        
        # Create chat completion with timeout
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=endpoint.modelId,
                messages=formatted_messages,
                stream=False
            ),
            timeout=60
        )
        
        return response.choices[0].message.content.strip()
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Timeout while querying {endpoint.name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error querying {endpoint.name}: {str(e)}"
        )

def extract_code_blocks(content: str) -> List[str]:
    """
    Extract code blocks from a message that uses the RUN-CODE syntax
    """
    code_blocks = []
    if "RUN-CODE" in content:
        matches = re.finditer(
            r'RUN-CODE\n```(?:python)?\n(.*?)\n```',
            content,
            re.DOTALL
        )
        code_blocks = [match.group(1).strip() for match in matches]
    return code_blocks

def extract_json_blocks(content: str) -> List[Dict[str, Any]]:
    """
    Extract JSON blocks from a message
    """
    json_blocks = []
    matches = re.finditer(r'```json\n(.*?)\n```', content, re.DOTALL)
    for match in matches:
        try:
            json_data = json.loads(match.group(1))
            json_blocks.append(json_data)
        except json.JSONDecodeError:
            continue
    return json_blocks

def should_continue_conversation(responses: List[Dict[str, Any]]) -> bool:
    """
    Analyze responses to determine if the conversation should continue
    """
    last_response = responses[-1]["content"]
    # Check if the last response ends with a question mark or contains a question-like phrase
    question_patterns = [
        r'\?$',  # Ends with question mark
        r'what (?:do|are|is|would|should|could|will|can) (?:you|we|they|it|i)\b',
        r'how (?:do|would|should|could|will|can) (?:you|we|they|it|i)\b',
        r'(?:could|would|can|will) (?:you|we|they|it|i)\b.*\?',
        r'\b(?:explain|describe|elaborate|clarify|tell me)\b'
    ]
    
    return any(re.search(pattern, last_response.lower()) for pattern in question_patterns)

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Process a chat request across multiple LLM endpoints with model interaction and auto-continuation
    """
    all_responses = []
    shared_context = ""
    turn_count = 0
    max_turns = request.max_turns or 5
    
    # Use default endpoints if none provided
    endpoints = request.endpoints if request.endpoints else DEFAULT_ENDPOINTS
    
    # Initial messages from the user
    current_messages = [msg.dict() for msg in request.messages]
    
    while turn_count < max_turns:
        responses = []
        
        # Process each endpoint sequentially
        for i, endpoint in enumerate(endpoints):
            try:
                # Get response from the model
                response = await query_llm(endpoint, current_messages, shared_context)
                
                # Add the model's response
                response_dict = {
                    "role": "assistant",
                    "name": endpoint.name,
                    "content": response
                }
                responses.append(response_dict)
                
                # Extract and execute any code blocks
                code_blocks = extract_code_blocks(response)
                for code in code_blocks:
                    output = run_code(code)
                    responses.append({
                        "role": "assistant",
                        "name": f"{endpoint.name}_Code_Output",
                        "content": f"Code execution output:\n{output}"
                    })
                
                # Extract any JSON data for model interaction
                json_blocks = extract_json_blocks(response)
                if json_blocks:
                    shared_context += f"\n{endpoint.name} provided structured data:\n"
                    for block in json_blocks:
                        shared_context += json.dumps(block, indent=2) + "\n"
                
                # Add response to shared context for subsequent models
                shared_context += f"\n{endpoint.name}'s response:\n{response}\n"
                    
                # Add a small delay between endpoints
                await asyncio.sleep(1)
                
            except Exception as e:
                responses.append({
                    "role": "assistant",
                    "name": f"{endpoint.name}_Error",
                    "content": f"Error: {str(e)}"
                })
                continue
        
        # Add this turn's responses to the overall list
        all_responses.extend(responses)
        
        # Update current messages for the next turn
        current_messages.extend([{
            "role": "assistant",
            "content": resp["content"],
            "name": resp["name"]
        } for resp in responses])
        
        # Check if we should continue the conversation
        if not request.auto_continue or not should_continue_conversation(responses):
            break
            
        turn_count += 1
    
    if not all_responses:
        raise HTTPException(
            status_code=500,
            detail="All endpoints failed to respond"
        )
    
    return {"responses": all_responses}

@app.post("/execute-code")
async def execute_code(request: CodeExecution):
    """
    Execute Python code and return the output
    """
    try:
        output = run_code(request.code, request.timeout)
        return {"output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint with environment validation
    """
    # Check if required environment variables are set
    missing_vars = []
    required_vars = [
        "MODEL_A_API_KEY",
        "MODEL_B_API_KEY",
        "MODEL_A_BASE_URL",
        "MODEL_B_BASE_URL"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return {
        "status": "healthy" if not missing_vars else "warning",
        "missing_env_vars": missing_vars,
        "default_endpoints": [
            {
                "name": endpoint.name,
                "model": endpoint.modelId
            } for endpoint in DEFAULT_ENDPOINTS
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting Multi-Model Chat Backend...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True
    )
