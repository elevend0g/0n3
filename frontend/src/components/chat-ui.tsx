import { useState } from 'react';
import { Send, Settings, AlertCircle } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  name?: string;
}

interface Endpoint {
  name: string;
  apiKey: string;
  baseUrl: string;
  modelId: string;
}

const defaultEndpoints: Endpoint[] = [
  {
    name: "Model A",
    apiKey: "",
    baseUrl: "https://openrouter.ai/api/v1",
    modelId: "anthropic/claude-3.5-sonnet"
  },
  {
    name: "Model B",
    apiKey: "",
    baseUrl: "https://api.openai.com/v1",
    modelId: "gpt-4"
  }
];

export default function ChatUI() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [endpoints, setEndpoints] = useState<Endpoint[]>(defaultEndpoints);
  const [showSettings, setShowSettings] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [autoContinue, setAutoContinue] = useState(false);
  const [maxTurns, setMaxTurns] = useState(5);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const activeEndpoints = endpoints.filter(endpoint => endpoint.apiKey.trim() !== '');
    if (activeEndpoints.length === 0) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Please configure at least one model endpoint in settings (gear icon) before chatting.',
        name: 'System'
      }]);
      return;
    }

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: input
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage],
          endpoints: activeEndpoints,
          auto_continue: autoContinue,
          max_turns: maxTurns
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Add assistant messages
      setMessages(prev => [...prev, ...data.responses]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error: Failed to get response from the server. Please check your API keys and endpoints in settings.',
        name: 'System'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEndpointUpdate = (index: number, field: keyof Endpoint, value: string) => {
    setEndpoints(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const addEndpoint = () => {
    setEndpoints(prev => [...prev, {
      name: `Model ${prev.length + 1}`,
      apiKey: '',
      baseUrl: 'https://api.openai.com/v1',
      modelId: 'gpt-3.5-turbo'
    }]);
  };

  const removeEndpoint = (index: number) => {
    setEndpoints(prev => prev.filter((_, i) => i !== index));
  };

  // Group messages by interaction
  const messageGroups = messages.reduce((groups: Message[][], message) => {
    if (message.role === 'user') {
      groups.push([message]);
    } else {
      if (groups.length === 0) {
        groups.push([message]);
      } else {
        const lastGroup = groups[groups.length - 1];
        const lastMessage = lastGroup[lastGroup.length - 1];
        if (lastMessage.role === 'user') {
          groups[groups.length - 1].push(message);
        } else {
          groups.push([message]);
        }
      }
    }
    return groups;
  }, []);

  return (
    <div className="container mx-auto p-4 max-w-4xl">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Multi-Model Chat</h1>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="p-2 rounded-full hover:bg-secondary"
          title="Settings"
        >
          <Settings className="w-6 h-6" />
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="mb-4 p-4 bg-card rounded-lg border">
          <h2 className="text-xl font-semibold mb-4">Model Endpoints</h2>
          
          {/* Auto-continue Settings */}
          <div className="mb-4 p-4 bg-secondary rounded-lg">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="autoContinue"
                  checked={autoContinue}
                  onChange={(e) => setAutoContinue(e.target.checked)}
                  className="w-4 h-4"
                />
                <label htmlFor="autoContinue" className="text-sm font-medium">
                  Enable Auto-continue
                </label>
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="maxTurns" className="text-sm font-medium">
                  Max Turns:
                </label>
                <input
                  type="number"
                  id="maxTurns"
                  value={maxTurns}
                  onChange={(e) => setMaxTurns(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-20 p-1 rounded border bg-background"
                  min="1"
                  max="20"
                />
              </div>
            </div>
          </div>

          {endpoints.map((endpoint, index) => (
            <div key={index} className="mb-4 p-4 bg-secondary rounded-lg">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Name</label>
                  <input
                    type="text"
                    value={endpoint.name}
                    onChange={(e) => handleEndpointUpdate(index, 'name', e.target.value)}
                    className="w-full p-2 rounded border bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">API Key</label>
                  <input
                    type="password"
                    value={endpoint.apiKey}
                    onChange={(e) => handleEndpointUpdate(index, 'apiKey', e.target.value)}
                    className="w-full p-2 rounded border bg-background"
                    placeholder="Enter your API key"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Base URL</label>
                  <input
                    type="text"
                    value={endpoint.baseUrl}
                    onChange={(e) => handleEndpointUpdate(index, 'baseUrl', e.target.value)}
                    className="w-full p-2 rounded border bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Model ID</label>
                  <input
                    type="text"
                    value={endpoint.modelId}
                    onChange={(e) => handleEndpointUpdate(index, 'modelId', e.target.value)}
                    className="w-full p-2 rounded border bg-background"
                  />
                </div>
              </div>
              <button
                onClick={() => removeEndpoint(index)}
                className="mt-2 px-3 py-1 text-sm text-destructive hover:bg-destructive/10 rounded"
              >
                Remove
              </button>
            </div>
          ))}
          <button
            onClick={addEndpoint}
            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
          >
            Add Endpoint
          </button>
        </div>
      )}

      {/* Chat Messages */}
      <div className="h-[60vh] overflow-y-auto mb-4 p-4 bg-card rounded-lg border">
        {messageGroups.map((group, groupIndex) => (
          <div key={groupIndex} className="mb-6">
            {group.map((message, index) => (
              <div
                key={index}
                className={`mb-2 p-4 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground ml-12'
                    : 'bg-secondary mr-12'
                }`}
              >
                {message.name && (
                  <div className="flex items-center gap-2 text-sm font-medium mb-1">
                    {message.name.includes('Error') ? (
                      <AlertCircle className="w-4 h-4 text-destructive" />
                    ) : null}
                    <span>{message.name}</span>
                  </div>
                )}
                <div className="whitespace-pre-wrap">
                  {message.content.split('```').map((part, i) => {
                    if (i % 2 === 0) {
                      return <span key={i}>{part}</span>;
                    } else {
                      const [lang, ...code] = part.split('\n');
                      return (
                        <pre key={i} className="bg-background p-2 rounded my-2 overflow-x-auto">
                          <div className="text-xs text-muted-foreground mb-1">{lang || 'plaintext'}</div>
                          <code>{code.join('\n')}</code>
                        </pre>
                      );
                    }
                  })}
                </div>
              </div>
            ))}
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-center items-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 p-4 rounded-lg border bg-background"
          disabled={isLoading}
        />
        <button
          type="submit"
          className={`p-4 bg-primary text-primary-foreground rounded-lg ${
            isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-primary/90'
          }`}
          disabled={isLoading}
        >
          <Send className="w-6 h-6" />
        </button>
      </form>
    </div>
  );
}
