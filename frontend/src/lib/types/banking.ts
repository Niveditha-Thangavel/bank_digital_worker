export interface BillingCycle {
  cycle_start: string;
  cycle_end: string;
  amount_due: number;
  amount_paid: number;
  payment_date: string;
}

export interface CreditCard {
  card_number: string;
  credit_limit: number;
  current_balance: number;
  billing_cycles: BillingCycle[];
}

export interface Loan {
  loan_id: string;
  loan_type: 'personal' | 'car' | 'home' | 'education';
  principal_amount: number;
  outstanding_amount: number;
  monthly_due: number;
  last_payment_date: string;
}

export interface CustomerAccount {
  customer_id: string;
  account_creation_date: string;
  credit_cards: CreditCard[];
  loans: Loan[];
}

export interface Transaction {
  date: string;
  amount: number;
  type: 'credit' | 'debit';
  description: string;
}

export interface BankStatement {
  customer_id: string;
  transactions: Transaction[];
}
