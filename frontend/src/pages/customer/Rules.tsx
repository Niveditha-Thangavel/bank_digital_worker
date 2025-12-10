import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';

const rules = [
  {
    id: 1,
    title: 'Income Check',
    description: 'Income must be ≥ ₹20,000 per month',
    category: 'Financial'
  },
  {
    id: 2,
    title: 'Account Age',
    description: 'Account must be ≥ 6 months old',
    category: 'Account'
  },
  {
    id: 3,
    title: 'Payment History',
    description: 'Late payments must be ≤ 2',
    category: 'Credit'
  },
  {
    id: 4,
    title: 'Transaction Issues',
    description: 'There must be no transaction anomalies',
    category: 'Account'
  },
  {
    id: 5,
    title: 'Credit Usage',
    description: 'Credit utilization must be < 70%',
    category: 'Credit'
  },
  {
    id: 6,
    title: 'Current Loans',
    description: 'Customer must have ≤ 1 active loan',
    category: 'Credit'
  },
  {
    id: 7,
    title: 'Income-Spend Health',
    description: 'Monthly income must show clear positive margin over spending',
    category: 'Financial'
  },
  {
    id: 8,
    title: 'Transaction Activity',
    description: 'Customer should have consistent and healthy transaction activity',
    category: 'Account'
  },
  {
    id: 9,
    title: 'Outlier Behavior',
    description: 'No extreme or unexplained large transaction outliers',
    category: 'Account'
  },
  {
    id: 10,
    title: 'Liquidity Buffer',
    description: 'Customer should maintain reasonable financial buffer or savings',
    category: 'Financial'
  },
  {
    id: 11,
    title: 'Credit History Strength',
    description: 'Customer must show reliable and stable historical credit behavior',
    category: 'Credit'
  }
];

const decisionRules = [
  { count: '11 rules satisfied', decision: 'APPROVE', color: 'success' },
  { count: '8-10 rules satisfied', decision: 'REVIEW', color: 'warning' },
  { count: '< 8 rules satisfied', decision: 'REJECT', color: 'destructive' }
];

export default function CustomerRules() {
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card">
        <h2 className="font-semibold text-foreground">Eligibility Rules</h2>
        <p className="text-sm text-muted-foreground">
          Understanding the criteria for loan approval
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 scrollbar-thin space-y-6">
        {/* Decision Summary */}
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Decision Criteria</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {decisionRules.map((rule) => (
              <Card key={rule.decision} className="p-4">
                <div className="flex items-center gap-3">
                  {rule.color === 'success' && (
                    <CheckCircle2 className="w-5 h-5 text-success" />
                  )}
                  {rule.color === 'warning' && (
                    <AlertCircle className="w-5 h-5 text-warning" />
                  )}
                  {rule.color === 'destructive' && (
                    <XCircle className="w-5 h-5 text-destructive" />
                  )}
                  <div>
                    <p className="font-medium text-foreground">{rule.decision}</p>
                    <p className="text-sm text-muted-foreground">{rule.count}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Rules List */}
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-3">
            All 11 Rules ({rules.length} total)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {rules.map((rule) => (
              <Card key={rule.id} className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-primary">{rule.id}</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium text-foreground">{rule.title}</h4>
                      <span className="text-xs bg-muted px-2 py-0.5 rounded text-muted-foreground">
                        {rule.category}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">{rule.description}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
