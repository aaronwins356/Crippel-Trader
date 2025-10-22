import React, { useState, useRef, useEffect } from 'react';

const ChatInterface = () => {
  const [messages, setMessages] = useState([
    { id: 1, role: 'system', content: 'Connection established. Awaiting user input.' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isSending) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputValue
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsSending(true);

    try {
      // Add placeholder for AI response
      const aiMessageId = Date.now() + 1;
      setMessages(prev => [...prev, {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        isStreaming: true
      }]);

      // Call our proxy endpoint
      const response = await fetch('/api/completion', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: "local-model",
          messages: [
            { role: "user", content: inputValue }
          ],
          stream: true
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';
      let messageId = aiMessageId;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            
            if (data === '[DONE]') {
              // Stream finished
              setMessages(prev => prev.map(msg => 
                msg.id === messageId 
                  ? { ...msg, isStreaming: false } 
                  : msg
              ));
              continue;
            }
            
            try {
              const parsed = JSON.parse(data);
              const content = parsed.choices[0]?.delta?.content || '';
              
              if (content) {
                accumulatedContent += content;
                setMessages(prev => prev.map(msg => 
                  msg.id === messageId 
                    ? { ...msg, content: accumulatedContent } 
                    : msg
                ));
              }
            } catch (e) {
              console.error('Error parsing JSON:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        id: Date.now() + 2,
        role: 'system',
        content: 'Error: Failed to get response from LLM. Please check if LM Studio is running.'
      }]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>MATRIX LLM TERMINAL</h1>
        <div className="connection-status">
          <span className="status-indicator"></span>
          CONNECTED TO LOCAL NODE
        </div>
      </div>
      
      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="message-content">
              {message.role === 'user' && '> user: '}
              {message.role === 'assistant' && '> ai: '}
              {message.role === 'system' && '> system: '}
              {message.content}
              {message.isStreaming && <span className="cursor-blink">█</span>}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input-container">
        <div className="input-wrapper">
          <span className="prompt">> user: </span>
          <textarea
            ref={inputRef}
            className="chat-input"
            value={inputValue}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            disabled={isSending}
            rows="1"
          />
          <button 
            className="send-button"
            onClick={handleSend}
            disabled={isSending || !inputValue.trim()}
          >
            {isSending ? 'SENDING...' : 'SEND'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;