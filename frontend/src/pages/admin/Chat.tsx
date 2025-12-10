import { useState } from 'react';
import { ChatInterface } from '@/components/ChatInterface';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';

export default function AdminChat() {
  const [customerId, setCustomerId] = useState('');

  return (
    <div className="h-full flex flex-col">
      {/* Customer ID Input */}
      <div className="p-4 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          <div className="flex-1 max-w-xs">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value.toUpperCase())}
                placeholder="Enter Customer ID (e.g., C101)"
                className="pl-9 uppercase"
              />
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            {customerId ? `Querying for: ${customerId}` : 'Enter a customer ID to query their data'}
          </p>
        </div>
      </div>

      {/* Chat Interface */}
      <div className="flex-1">
        <ChatInterface showQuickActions={true} />
      </div>
    </div>
  );
}
