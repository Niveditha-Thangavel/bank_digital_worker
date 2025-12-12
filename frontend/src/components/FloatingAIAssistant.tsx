import { useState } from 'react';
import { MessageSquare, X, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { sendAdminChatMessage} from '@/lib/api';
import { toast } from 'sonner';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

/* ------------------------- 🧠 PARSE MARKDOWN TABLE ------------------------ */
function parseMarkdownTable(text: string) {
  if (!text.includes("|")) return null;

  const lines = text.trim().split("\n").filter(line => line.includes("|"));

  if (lines.length < 3) return null;

  const headers = lines[0]
    .split("|")
    .map(h => h.trim())
    .filter(Boolean);

  const rows = lines.slice(2).map(row =>
    row
      .split("|")
      .map(col => col.trim())
      .filter(Boolean)
  );

  return rows.map((cols) => ({
    id: cols[0],
    customerId: cols[1],
    decision: cols[2],
    reason: cols[3]
  }));
}

/* ------------------------- 📦 CUSTOM TABLE ROW UI ------------------------- */
function DecisionTable({ rows }: any) {
  const [openRow, setOpenRow] = useState<string | null>(null);

  return (
    <div className="border rounded-md p-3 bg-background text-sm shadow-sm space-y-3">
      <table className="w-full text-left text-sm border-collapse">
        <thead>
          <tr className="border-b">
            <th className="py-1 font-semibold">Customer ID</th>
            <th className="py-1 font-semibold">Decision</th>
            <th className="py-1 font-semibold">Reason</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row: any) => (
            <>
              <tr key={row.id} className="border-b">
                <td className="py-2">{row.customerId}</td>
                <td className="py-2">{row.decision}</td>
                <td className="py-2">
                  <button
                    className="text-primary underline text-xs"
                    onClick={() => setOpenRow(openRow === row.id ? null : row.id)}
                  >
                    {openRow === row.id ? "Hide Reason" : "View Reason"}
                  </button>
                </td>
              </tr>
              {openRow === row.id && (
                <tr>
                  <td colSpan={4} className="p-3 bg-muted rounded text-xs">
                    {row.reason}
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------- FLOATING ASSISTANT ------------------------- */

export function FloatingAIAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>();

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await sendAdminChatMessage(userMessage, undefined, sessionId);
      setSessionId(response.session_id);
      setMessages(prev => [...prev, { role: 'assistant', content: response.reply }]);
    } catch (error) {
      toast.error('Failed to get response from AI');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          "fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-primary text-primary-foreground shadow-lg flex items-center justify-center hover:bg-primary/90 transition-all",
          isOpen && "hidden"
        )}
      >
        <MessageSquare className="w-6 h-6" />
      </button>

      {/* Chat Panel */}
      <div
        className={cn(
          "fixed bottom-6 right-6 z-50 w-96 h-[500px] bg-card border border-border rounded-lg shadow-2xl flex flex-col transition-all duration-300",
          isOpen ? "opacity-100 scale-100" : "opacity-0 scale-95 pointer-events-none"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground text-sm">AI Assistant</h3>
              <p className="text-xs text-muted-foreground">Customer data & approvals</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)}>
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Messages */}
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-muted-foreground text-sm py-8">
                Ask me about customer data, loan approvals, or any banking queries.
              </div>
            )}

            {messages.map((msg, i) => {
              const parsedRows =
                msg.role === "assistant" ? parseMarkdownTable(msg.content) : null;

              return (
                <div
                  key={i}
                  className={cn(
                    "max-w-[80%] p-3 rounded-lg text-sm",
                    msg.role === 'user'
                      ? "ml-auto bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  )}
                >
                  {parsedRows ? (
                    <DecisionTable rows={parsedRows} />
                  ) : (
                    msg.content
                  )}
                </div>
              );
            })}

            {isLoading && (
              <div className="bg-muted text-foreground max-w-[80%] p-3 rounded-lg text-sm">
                <span className="animate-pulse">Thinking...</span>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="p-4 border-t border-border">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about customers..."
              className="flex-1"
              disabled={isLoading}
            />
            <Button onClick={handleSend} size="icon" disabled={isLoading || !input.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}