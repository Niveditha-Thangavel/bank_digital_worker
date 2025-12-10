import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { Plus, Minus, Loader2 } from 'lucide-react';
import { getCustomerData, saveCustomerData, CustomerData } from '@/lib/api';

interface BillingCycle {
  cycle_start: string;
  cycle_end: string;
  amount_due: number;
  amount_paid: number;
  payment_date: string;
}

interface CreditCard {
  card_number: string;
  credit_limit: number;
  current_balance: number;
  billing_cycles: BillingCycle[];
}

interface Loan {
  loan_id: string;
  loan_type: string;
  principal_amount: number;
  outstanding_amount: number;
  monthly_due: number;
  last_payment_date: string;
}

interface Transaction {
  date: string;
  amount: number;
  type: 'credit' | 'debit';
  description: string;
}

const today = new Date().toISOString().split('T')[0];

const emptyBillingCycle = (): BillingCycle => ({
  cycle_start: today,
  cycle_end: today,
  amount_due: 0,
  amount_paid: 0,
  payment_date: today,
});

const emptyCreditCard = (): CreditCard => ({
  card_number: '',
  credit_limit: 0,
  current_balance: 0,
  billing_cycles: [emptyBillingCycle()],
});

const emptyLoan = (): Loan => ({
  loan_id: '',
  loan_type: '',
  principal_amount: 0,
  outstanding_amount: 0,
  monthly_due: 0,
  last_payment_date: today,
});

const emptyTransaction = (): Transaction => ({
  date: today,
  amount: 0,
  type: 'credit',
  description: '',
});

export default function CustomerDataPage() {
  const [customerId, setCustomerId] = useState('');
  const [accountCreationDate, setAccountCreationDate] = useState(today);
  const [transactions, setTransactions] = useState<Transaction[]>([emptyTransaction()]);
  const [creditCards, setCreditCards] = useState<CreditCard[]>([emptyCreditCard()]);
  const [loans, setLoans] = useState<Loan[]>([emptyLoan()]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isExisting, setIsExisting] = useState(false);

  const loadCustomerData = useCallback(async (id: string) => {
    if (!id || id.length < 2) return;
    
    setIsLoading(true);
    try {
      const data = await getCustomerData(id);
      if (data) {
        setIsExisting(true);
        setAccountCreationDate(data.account_creation_date || today);
        setCreditCards(data.credit_cards?.length ? data.credit_cards : [emptyCreditCard()]);
        setLoans(data.loans?.length ? data.loans : [emptyLoan()]);
        setTransactions(data.transactions?.length ? data.transactions : [emptyTransaction()]);
        toast.success(`Loaded data for customer ${id}`);
      } else {
        setIsExisting(false);
        // Reset to defaults for new customer
        setAccountCreationDate(today);
        setCreditCards([emptyCreditCard()]);
        setLoans([emptyLoan()]);
        setTransactions([emptyTransaction()]);
      }
    } catch (error) {
      console.error('Error loading customer data:', error);
      setIsExisting(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounced customer ID lookup
  useEffect(() => {
    const timer = setTimeout(() => {
      if (customerId.length >= 2) {
        loadCustomerData(customerId);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [customerId, loadCustomerData]);

  const updateCount = (type: 'transactions' | 'creditCards' | 'loans', delta: number) => {
    if (type === 'transactions') {
      if (delta > 0) {
        setTransactions([...transactions, emptyTransaction()]);
      } else if (transactions.length > 1) {
        setTransactions(transactions.slice(0, -1));
      }
    } else if (type === 'creditCards') {
      if (delta > 0) {
        setCreditCards([...creditCards, emptyCreditCard()]);
      } else if (creditCards.length > 1) {
        setCreditCards(creditCards.slice(0, -1));
      }
    } else if (type === 'loans') {
      if (delta > 0) {
        setLoans([...loans, emptyLoan()]);
      } else if (loans.length > 1) {
        setLoans(loans.slice(0, -1));
      }
    }
  };

  const updateBillingCycleCount = (cardIndex: number, delta: number) => {
    const updated = [...creditCards];
    if (delta > 0) {
      updated[cardIndex].billing_cycles.push(emptyBillingCycle());
    } else if (updated[cardIndex].billing_cycles.length > 1) {
      updated[cardIndex].billing_cycles.pop();
    }
    setCreditCards(updated);
  };

  const updateTransaction = (index: number, field: keyof Transaction, value: string | number) => {
    const updated = [...transactions];
    updated[index] = { ...updated[index], [field]: value };
    setTransactions(updated);
  };

  const updateCreditCard = (index: number, field: keyof CreditCard, value: string | number) => {
    const updated = [...creditCards];
    updated[index] = { ...updated[index], [field]: value };
    setCreditCards(updated);
  };

  const updateBillingCycle = (cardIndex: number, cycleIndex: number, field: keyof BillingCycle, value: string | number) => {
    const updated = [...creditCards];
    updated[cardIndex].billing_cycles[cycleIndex] = {
      ...updated[cardIndex].billing_cycles[cycleIndex],
      [field]: value,
    };
    setCreditCards(updated);
  };

  const updateLoan = (index: number, field: keyof Loan, value: string | number) => {
    const updated = [...loans];
    updated[index] = { ...updated[index], [field]: value };
    setLoans(updated);
  };

  const handleSave = async () => {
    if (!customerId) {
      toast.error('Please enter a Customer ID');
      return;
    }
    
    setIsSaving(true);
    try {
      const customerData: CustomerData = {
        customer_id: customerId,
        account_creation_date: accountCreationDate,
        credit_cards: creditCards,
        loans: loans,
        transactions: transactions,
      };

      await saveCustomerData(customerData);
      setIsExisting(true);
      toast.success(isExisting ? 'Customer data updated' : 'Customer data created');
    } catch (error) {
      console.error('Error saving customer data:', error);
      toast.error('Failed to save customer data');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex-1 overflow-auto p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Loan Approval Checker</h1>
          <p className="text-muted-foreground mt-1">
            Enter a customer ID to load existing data or create new customer records.
          </p>
        </div>

        {/* Customer & Account + Counts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-foreground">Customer & Account</h2>
            <div className="space-y-3">
              <div>
                <Label className="text-muted-foreground text-sm">Customer ID (format C101)</Label>
                <div className="relative">
                  <Input
                    value={customerId}
                    onChange={(e) => setCustomerId(e.target.value.toUpperCase())}
                    placeholder="C101"
                    className="bg-muted border-0"
                  />
                  {isLoading && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-muted-foreground" />
                  )}
                </div>
                {customerId && !isLoading && (
                  <p className="text-xs mt-1 text-muted-foreground">
                    {isExisting ? '✓ Existing customer loaded' : 'New customer - will be created on save'}
                  </p>
                )}
              </div>
              <div>
                <Label className="text-muted-foreground text-sm">Account creation date</Label>
                <Input
                  type="date"
                  value={accountCreationDate}
                  onChange={(e) => setAccountCreationDate(e.target.value)}
                  className="bg-muted border-0"
                />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-foreground">Counts</h2>
            <div className="space-y-3">
              <CounterInput
                label="Number of transactions"
                value={transactions.length}
                onIncrement={() => updateCount('transactions', 1)}
                onDecrement={() => updateCount('transactions', -1)}
              />
              <CounterInput
                label="Number of credit cards"
                value={creditCards.length}
                onIncrement={() => updateCount('creditCards', 1)}
                onDecrement={() => updateCount('creditCards', -1)}
              />
              <CounterInput
                label="Number of loans"
                value={loans.length}
                onIncrement={() => updateCount('loans', 1)}
                onDecrement={() => updateCount('loans', -1)}
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Transactions */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-foreground">Transactions</h2>
          <div className="space-y-4">
            {transactions.map((tx, i) => (
              <div key={i} className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <Label className="text-muted-foreground text-sm">Tx {i + 1} date</Label>
                  <Input
                    type="date"
                    value={tx.date}
                    onChange={(e) => updateTransaction(i, 'date', e.target.value)}
                    className="bg-muted border-0"
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-sm">Tx {i + 1} amount</Label>
                  <NumberInput
                    value={tx.amount}
                    onChange={(val) => updateTransaction(i, 'amount', val)}
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-sm">Tx {i + 1} type</Label>
                  <Select value={tx.type} onValueChange={(val) => updateTransaction(i, 'type', val)}>
                    <SelectTrigger className="bg-muted border-0">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="credit">credit</SelectItem>
                      <SelectItem value="debit">debit</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-muted-foreground text-sm">Tx {i + 1} description</Label>
                  <Input
                    value={tx.description}
                    onChange={(e) => updateTransaction(i, 'description', e.target.value)}
                    className="bg-muted border-0"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <Separator />

        {/* Credit Cards */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-foreground">Credit Cards</h2>
          {creditCards.map((card, cardIndex) => (
            <div key={cardIndex} className="space-y-4">
              <h3 className="text-lg font-medium text-foreground">Card {cardIndex + 1}</h3>
              <div className="space-y-3">
                <div>
                  <Label className="text-muted-foreground text-sm">Card {cardIndex + 1} number</Label>
                  <Input
                    value={card.card_number}
                    onChange={(e) => updateCreditCard(cardIndex, 'card_number', e.target.value)}
                    className="bg-muted border-0"
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-sm">Card {cardIndex + 1} credit_limit</Label>
                  <NumberInput
                    value={card.credit_limit}
                    onChange={(val) => updateCreditCard(cardIndex, 'credit_limit', val)}
                  />
                </div>
                <div>
                  <Label className="text-muted-foreground text-sm">Card {cardIndex + 1} current_balance</Label>
                  <NumberInput
                    value={card.current_balance}
                    onChange={(val) => updateCreditCard(cardIndex, 'current_balance', val)}
                  />
                </div>
                <CounterInput
                  label={`Card ${cardIndex + 1} billing cycles count`}
                  value={card.billing_cycles.length}
                  onIncrement={() => updateBillingCycleCount(cardIndex, 1)}
                  onDecrement={() => updateBillingCycleCount(cardIndex, -1)}
                />
                
                {card.billing_cycles.map((cycle, cycleIndex) => (
                  <div key={cycleIndex} className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <Label className="text-muted-foreground text-sm">cycle {cycleIndex + 1} start</Label>
                      <Input
                        type="date"
                        value={cycle.cycle_start}
                        onChange={(e) => updateBillingCycle(cardIndex, cycleIndex, 'cycle_start', e.target.value)}
                        className="bg-muted border-0"
                      />
                    </div>
                    <div>
                      <Label className="text-muted-foreground text-sm">cycle {cycleIndex + 1} end</Label>
                      <Input
                        type="date"
                        value={cycle.cycle_end}
                        onChange={(e) => updateBillingCycle(cardIndex, cycleIndex, 'cycle_end', e.target.value)}
                        className="bg-muted border-0"
                      />
                    </div>
                    <div>
                      <Label className="text-muted-foreground text-sm">cycle {cycleIndex + 1} amount_due</Label>
                      <NumberInput
                        value={cycle.amount_due}
                        onChange={(val) => updateBillingCycle(cardIndex, cycleIndex, 'amount_due', val)}
                      />
                    </div>
                    <div>
                      <Label className="text-muted-foreground text-sm">cycle {cycleIndex + 1} amount_paid</Label>
                      <NumberInput
                        value={cycle.amount_paid}
                        onChange={(val) => updateBillingCycle(cardIndex, cycleIndex, 'amount_paid', val)}
                      />
                    </div>
                    <div className="md:col-span-4">
                      <Label className="text-muted-foreground text-sm">cycle {cycleIndex + 1} payment_date</Label>
                      <Input
                        type="date"
                        value={cycle.payment_date}
                        onChange={(e) => updateBillingCycle(cardIndex, cycleIndex, 'payment_date', e.target.value)}
                        className="bg-muted border-0"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <Separator />

        {/* Loans */}
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-foreground">Loans</h2>
          {loans.map((loan, i) => (
            <div key={i} className="space-y-3">
              <h3 className="text-lg font-medium text-foreground">Loan {i + 1}</h3>
              <div>
                <Label className="text-muted-foreground text-sm">Loan {i + 1} id</Label>
                <Input
                  value={loan.loan_id}
                  onChange={(e) => updateLoan(i, 'loan_id', e.target.value)}
                  className="bg-muted border-0"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-sm">Loan {i + 1} type</Label>
                <Input
                  value={loan.loan_type}
                  onChange={(e) => updateLoan(i, 'loan_type', e.target.value)}
                  className="bg-muted border-0"
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-sm">Loan {i + 1} principal_amount</Label>
                <NumberInput
                  value={loan.principal_amount}
                  onChange={(val) => updateLoan(i, 'principal_amount', val)}
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-sm">Loan {i + 1} outstanding_amount</Label>
                <NumberInput
                  value={loan.outstanding_amount}
                  onChange={(val) => updateLoan(i, 'outstanding_amount', val)}
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-sm">Loan {i + 1} monthly_due</Label>
                <NumberInput
                  value={loan.monthly_due}
                  onChange={(val) => updateLoan(i, 'monthly_due', val)}
                />
              </div>
              <div>
                <Label className="text-muted-foreground text-sm">Loan {i + 1} last_payment_date</Label>
                <Input
                  type="date"
                  value={loan.last_payment_date}
                  onChange={(e) => updateLoan(i, 'last_payment_date', e.target.value)}
                  className="bg-muted border-0"
                />
              </div>
            </div>
          ))}
        </div>

        <Separator />

        {/* Actions */}
        <div className="flex flex-wrap gap-4 pb-8">
          <Button onClick={handleSave} variant="outline" disabled={isSaving || !customerId}>
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              isExisting ? 'Update Customer Data' : 'Create Customer'
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

function CounterInput({
  label,
  value,
  onIncrement,
  onDecrement,
}: {
  label: string;
  value: number;
  onIncrement: () => void;
  onDecrement: () => void;
}) {
  return (
    <div>
      <Label className="text-muted-foreground text-sm">{label}</Label>
      <div className="flex items-center bg-muted rounded-md">
        <Input
          type="number"
          value={value}
          readOnly
          className="bg-transparent border-0 flex-1"
        />
        <Button variant="ghost" size="icon" onClick={onDecrement} className="h-10 w-10">
          <Minus className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={onIncrement} className="h-10 w-10">
          <Plus className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

function NumberInput({
  value,
  onChange,
}: {
  value: number;
  onChange: (val: number) => void;
}) {
  return (
    <div className="flex items-center bg-muted rounded-md">
      <Input
        type="number"
        step="0.01"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="bg-transparent border-0 flex-1"
      />
      <Button variant="ghost" size="icon" onClick={() => onChange(value - 1)} className="h-10 w-10">
        <Minus className="w-4 h-4" />
      </Button>
      <Button variant="ghost" size="icon" onClick={() => onChange(value + 1)} className="h-10 w-10">
        <Plus className="w-4 h-4" />
      </Button>
    </div>
  );
}
