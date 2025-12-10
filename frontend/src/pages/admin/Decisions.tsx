import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, Eye, Edit2, X, Save } from 'lucide-react';
import { getDecisions, updateDecision, DecisionsMap, Decision } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

export default function AdminDecisions() {
  const { toast } = useToast();
  const [decisions, setDecisions] = useState<DecisionsMap>({});
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editDecision, setEditDecision] = useState<'APPROVE' | 'REJECT' | 'REVIEW'>('REVIEW');
  const [editReason, setEditReason] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const fetchDecisions = async () => {
    try {
      const data = await getDecisions();
      setDecisions(data);
    } catch (error) {
      console.error('Failed to fetch decisions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions();
  }, []);

  const handleViewReason = (customerId: string) => {
    setSelectedCustomer(customerId);
    setIsEditing(false);
  };

  const handleEdit = (customerId: string) => {
    const decision = decisions[customerId];
    setSelectedCustomer(customerId);
    setEditDecision(decision.decision);
    setEditReason(decision.reason);
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!selectedCustomer) return;
    
    setIsSaving(true);
    try {
      await updateDecision(selectedCustomer, editDecision, editReason);
      await fetchDecisions();
      toast({
        title: 'Decision updated',
        description: `Decision for ${selectedCustomer} has been updated.`
      });
      setSelectedCustomer(null);
      setIsEditing(false);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update decision. Please try again.',
        variant: 'destructive'
      });
    } finally {
      setIsSaving(false);
    }
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'APPROVE':
        return <CheckCircle className="w-5 h-5 text-success" />;
      case 'REJECT':
        return <XCircle className="w-5 h-5 text-destructive" />;
      default:
        return <AlertCircle className="w-5 h-5 text-warning" />;
    }
  };

  const getDecisionBadge = (decision: string) => {
    const styles = {
      APPROVE: 'bg-success/10 text-success border-success/20',
      REJECT: 'bg-destructive/10 text-destructive border-destructive/20',
      REVIEW: 'bg-warning/10 text-warning border-warning/20'
    };
    return styles[decision as keyof typeof styles] || styles.REVIEW;
  };

  const decisionEntries = Object.entries(decisions);
  const stats = {
    approved: decisionEntries.filter(([, d]) => d.decision === 'APPROVE').length,
    rejected: decisionEntries.filter(([, d]) => d.decision === 'REJECT').length,
    review: decisionEntries.filter(([, d]) => d.decision === 'REVIEW').length
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card">
        <h2 className="font-semibold text-foreground">Decision Summary</h2>
        <p className="text-sm text-muted-foreground">View and manage loan decisions</p>
      </div>

      {/* Stats */}
      <div className="p-4 border-b border-border bg-card/50">
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-foreground">{decisionEntries.length}</p>
            <p className="text-sm text-muted-foreground">Total</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-success">{stats.approved}</p>
            <p className="text-sm text-muted-foreground">Approved</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-warning">{stats.review}</p>
            <p className="text-sm text-muted-foreground">Review</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-destructive">{stats.rejected}</p>
            <p className="text-sm text-muted-foreground">Rejected</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-pulse-soft text-muted-foreground">Loading decisions...</div>
          </div>
        ) : decisionEntries.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
              <AlertCircle className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium text-foreground mb-2">No decisions yet</h3>
            <p className="text-muted-foreground max-w-sm">
              Loan decisions will appear here once customers are evaluated.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {decisionEntries.map(([customerId, decision]) => (
              <Card key={customerId} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getDecisionIcon(decision.decision)}
                    <div>
                      <h4 className="font-medium text-foreground">{customerId}</h4>
                      <p className="text-sm text-muted-foreground">
                        Updated: {new Date(decision.updated_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      'px-3 py-1 rounded-full text-sm font-medium border',
                      getDecisionBadge(decision.decision)
                    )}>
                      {decision.decision}
                    </span>
                    <Button variant="ghost" size="icon" onClick={() => handleViewReason(customerId)}>
                      <Eye className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleEdit(customerId)}>
                      <Edit2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Dialog */}
      <Dialog open={!!selectedCustomer} onOpenChange={() => setSelectedCustomer(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {isEditing ? 'Edit Decision' : 'Decision Details'} - {selectedCustomer}
            </DialogTitle>
          </DialogHeader>
          
          {selectedCustomer && (
            <div className="space-y-4">
              {isEditing ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1.5">
                      Decision
                    </label>
                    <Select value={editDecision} onValueChange={(v) => setEditDecision(v as any)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="APPROVE">APPROVE</SelectItem>
                        <SelectItem value="REVIEW">REVIEW</SelectItem>
                        <SelectItem value="REJECT">REJECT</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1.5">
                      Reason
                    </label>
                    <Textarea
                      value={editReason}
                      onChange={(e) => setEditReason(e.target.value)}
                      rows={4}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleSave} disabled={isSaving} className="flex-1">
                      <Save className="w-4 h-4 mr-2" />
                      {isSaving ? 'Saving...' : 'Save Changes'}
                    </Button>
                    <Button variant="outline" onClick={() => setIsEditing(false)}>
                      Cancel
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2 mb-4">
                    {getDecisionIcon(decisions[selectedCustomer]?.decision)}
                    <span className={cn(
                      'px-3 py-1 rounded-full text-sm font-medium border',
                      getDecisionBadge(decisions[selectedCustomer]?.decision)
                    )}>
                      {decisions[selectedCustomer]?.decision}
                    </span>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-muted-foreground mb-1">Reason</h4>
                    <p className="text-foreground whitespace-pre-wrap">
                      {decisions[selectedCustomer]?.reason || 'No reason provided'}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => setIsEditing(true)} className="flex-1">
                      <Edit2 className="w-4 h-4 mr-2" />
                      Edit Decision
                    </Button>
                    <Button variant="outline" onClick={() => setSelectedCustomer(null)}>
                      Close
                    </Button>
                  </div>
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
