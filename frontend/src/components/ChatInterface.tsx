import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { sendChatMessage, ChatMessage } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';

interface ChatInterfaceProps {
  showQuickActions?: boolean;
}

const quickActions = [
  'Check eligibility for my loan',
  'Show my credit and loan details',
  'Explain my credit score',
];

export function ChatInterface({ showQuickActions = true }: ChatInterfaceProps) {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (messageText?: string) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', text }]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(
        text,
        user?.customerId,
        sessionId || undefined
      );
      
      setSessionId(response.session_id);
      
      const replyText = typeof response.reply === 'string' 
        ? response.reply 
        : JSON.stringify(response.reply, null, 2);
      
      setMessages(prev => [...prev, { role: 'assistant', text: replyText }]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        text: 'Sorry, I encountered an error. Please make sure the backend server is running and try again.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewConversation = () => {
    setMessages([]);
    setSessionId(null);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-card">
        <div>
          <h2 className="font-semibold text-foreground">Chat</h2>
          <p className="text-sm text-muted-foreground">Ask about loans, eligibility, and more</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleNewConversation}>
          New Conversation
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-primary" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">Hi, I'm your Banking Agent</h3>
            <p className="text-muted-foreground max-w-md mb-6">
              Ask about a loan and I'll confirm the customer ID, fetch bank statements, credit cards, 
              and loans, run the rules, and share a clear decision with reasons.
            </p>
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <Sparkles className="w-4 h-4" />
              Start by asking a question or tap a quick prompt below
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={cn(
                'flex gap-3 animate-fade-in',
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-foreground" />
                </div>
              )}
              <div
                className={cn(
                  'max-w-[70%] whitespace-pre-wrap',
                  msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-agent'
                )}
              >
                {msg.text}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-muted-foreground" />
                </div>
              )}
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-primary-foreground" />
            </div>
            <div className="chat-bubble-agent flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {showQuickActions && messages.length === 0 && (
        <div className="px-6 pb-4">
          <div className="flex flex-wrap gap-2 justify-center">
            {quickActions.map((action, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(action)}
                className="quick-action-btn"
                disabled={isLoading}
              >
                {action}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-border bg-card">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-3"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask to check eligibility, explain the score..."
            className="flex-1"
            disabled={isLoading}
          />
          <Button type="submit" disabled={!input.trim() || isLoading}>
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
