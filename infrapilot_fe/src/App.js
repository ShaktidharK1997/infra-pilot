import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from "react-oidc-context";
import { MessageCircle, Send, LogOut } from 'lucide-react';

function App() {
  const auth = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [apiClient, setApiClient] = useState(null);
  const messagesEndRef = useRef(null);
  const [loading, setLoading] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const signOutRedirect = () => {
    const clientId = "4jk1ku62b3i9veegqirlptjusf";
    const logoutUri = "https://infrapilot-fe.s3-website-us-east-1.amazonaws.com";
    const cognitoDomain = "https://us-east-1pk76jhr5v.auth.us-east-1.amazoncognito.com";
    window.location.href = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(logoutUri)}`;
  };



  useEffect(() => {
    if (auth.isAuthenticated && window.apigClientFactory) {
      const client = window.apigClientFactory.newClient({
        region: 'us-east-1'
      });
      setApiClient(client);
    }
  }, [auth.isAuthenticated]);

  const formatTime = () => {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
  };

  const sendMessage = async () => {
    if (!input.trim() || !apiClient) return;

    const userMessage = {
      text: input,
      sender: 'user',
      time: formatTime()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await apiClient.chatPost({}, 
        { message: input },
        { headers: { 
          'Authorization': auth.user?.id_token,
          'Content-Type': 'application/json'
        }}
      );
      
      if (response.data) {
        setMessages(prev => [...prev, {
          text: response.data.response,
          sender: 'bot',
          time: formatTime()
        }]);
      }
    } catch (err) {
      console.error('Error:', err);
      setMessages(prev => [...prev, {
        text: "Sorry, I encountered an error. Please try again.",
        sender: 'bot',
        time: formatTime()
      }]);
    } finally {
      setLoading(false);
    }
  };

  if (auth.isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center">
          <div className="w-12 h-12 bg-blue-200 rounded-full mb-4"></div>
          <div className="text-gray-600">Loading...</div>
        </div>
      </div>
    );
  }

  if (auth.error) {
    return (
      <div className="h-screen flex items-center justify-center text-red-600">
        <div className="bg-red-50 p-6 rounded-lg">
          <h2 className="text-xl font-bold mb-2">Error</h2>
          <p>{auth.error.message}</p>
        </div>
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold mb-4 text-blue-900">Welcome to InfraPilot</h1>
          <p className="text-gray-600">Your AI-powered DevOps Assistant</p>
        </div>
        <div className="w-96 bg-white rounded-xl shadow-xl overflow-hidden mb-8 transform transition-all hover:scale-105">
          <div className="p-6 border-b">
            <div className="flex items-center space-x-4 mb-4">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <MessageCircle className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800">Chat Interface</h3>
                <p className="text-sm text-gray-500">Sign in to start chatting</p>
              </div>
            </div>
          </div>
          <div className="p-6 bg-gray-50">
            <div className="flex gap-4">
              <input
                disabled
                className="flex-1 p-3 border rounded-lg bg-gray-100 text-gray-400"
                placeholder="Sign in to start chatting..."
              />
              <button disabled className="p-3 bg-gray-300 text-white rounded-lg">
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
        <button
          onClick={() => auth.signinRedirect()}
          className="px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transform transition-all hover:scale-105 shadow-lg"
        >
          Sign in to Access
        </button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="bg-white p-4 shadow-md flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <MessageCircle className="w-6 h-6 text-blue-600" />
          </div>
          <span className="text-gray-700 font-medium">{auth.user?.profile.email}</span>
        </div>
        <button
          onClick={() => signOutRedirect()}
          className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>Sign out</span>
        </button>
      </div>

      <div className="flex-1 p-4 overflow-y-auto">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-8 p-8 bg-white rounded-lg shadow-sm">
              <MessageCircle className="w-12 h-12 mx-auto mb-4 text-blue-300" />
              <p className="text-lg">Start a conversation with InfraPilot</p>
              <p className="text-sm text-gray-400">Ask me about DevOps tasks and infrastructure management</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className="max-w-sm flex flex-col">
                  <div
                    className={`p-4 rounded-2xl ${
                      message.sender === 'user'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-white text-gray-800 rounded-bl-none shadow-sm'
                    }`}
                  >
                    {message.text}
                  </div>
                  <span className={`text-xs mt-1 ${message.sender === 'user' ? 'text-right' : 'text-left'} text-gray-500`}>
                    {message.time}
                  </span>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white p-4 rounded-2xl rounded-bl-none shadow-sm">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      
      <div className="border-t bg-white p-4 shadow-lg">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-4 items-center bg-gray-50 p-2 rounded-lg border">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type your message..."
              className="flex-1 p-2 bg-transparent focus:outline-none"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;