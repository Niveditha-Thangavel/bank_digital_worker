import { useState, useEffect } from 'react';
import { History as HistoryIcon, MessageSquare, Calendar, ChevronRight, Users } from 'lucide-react';
import { getSessions } from '@/lib/api';
import { Card } from '@/components/ui/card';

interface SessionSummary {
  id: string;
  currentLen: number;
  historyLen: number;
}

export default function AdminHistory() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const data = await getSessions();
        const sessionList = Object.entries(data).map(([id, info]) => ({
          id,
          currentLen: info.current_len,
          historyLen: info.history_len
        }));
        setSessions(sessionList);
      } catch (error) {
        console.error('Failed to fetch sessions:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSessions();
  }, []);

  const totalMessages = sessions.reduce((acc, s) => acc + s.currentLen, 0);
  const totalArchived = sessions.reduce((acc, s) => acc + s.historyLen, 0);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card">
        <h2 className="font-semibold text-foreground">All Chat Sessions</h2>
        <p className="text-sm text-muted-foreground">View all customer conversations</p>
      </div>

      {/* Stats */}
      <div className="p-4 border-b border-border bg-card/50">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">{sessions.length}</p>
            <p className="text-sm text-muted-foreground">Total Sessions</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">{totalMessages}</p>
            <p className="text-sm text-muted-foreground">Active Messages</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">{totalArchived}</p>
            <p className="text-sm text-muted-foreground">Archived</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-pulse-soft text-muted-foreground">Loading sessions...</div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
              <Users className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium text-foreground mb-2">No sessions yet</h3>
            <p className="text-muted-foreground max-w-sm">
              Customer chat sessions will appear here.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => (
              <Card
                key={session.id}
                className="p-4 hover:bg-accent/50 transition-colors cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <MessageSquare className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <h4 className="font-medium text-foreground font-mono">
                        {session.id.slice(0, 8)}...
                      </h4>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{session.currentLen} messages</span>
                        {session.historyLen > 0 && (
                          <span className="text-xs bg-muted px-2 py-0.5 rounded">
                            {session.historyLen} archived
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
