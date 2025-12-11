const API_BASE = 'http://localhost:8000';

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
}

export interface ChatResponse {
  reply: string;
  session_id: string;
  current_session: ChatMessage[];
  warning?: string;
}

export interface Decision {
  decision: 'APPROVE' | 'REJECT' | 'REVIEW';
  reason: string;
  updated_at: string;
}

export interface DecisionsMap {
  [customerId: string]: Decision;
}

export async function sendChatMessage(
  message: string,
  customerId?: string,
  sessionId?: string,
  endSession?: boolean
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      customer_id: customerId,
      session_id: sessionId,
      end_session: endSession
    })
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getDecisions(): Promise<DecisionsMap> {
  const response = await fetch(`${API_BASE}/decisions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch decisions: ${response.statusText}`);
  }
  const data = await response.json();
  return data.decisions || {};
}

export async function updateDecision(
  customerId: string,
  decision: string,
  reason: string
): Promise<void> {
  const response = await fetch(`${API_BASE}/update-decisions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer_id: customerId,
      decision,
      reason
    })
  });

  if (!response.ok) {
    throw new Error(`Failed to update decision: ${response.statusText}`);
  }
}

export async function getSessions(): Promise<Record<string, { current_len: number; history_len: number }>> {
  const response = await fetch(`${API_BASE}/sessions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.statusText}`);
  }
  const data = await response.json();
  return data.sessions || {};
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export interface CustomerData {
  customer_id: string;
  account_creation_date: string;
  credit_cards: Array<{
    card_number: string;
    credit_limit: number;
    current_balance: number;
    billing_cycles: Array<{
      cycle_start: string;
      cycle_end: string;
      amount_due: number;
      amount_paid: number;
      payment_date: string;
    }>;
  }>;
  loans: Array<{
    loan_id: string;
    loan_type: string;
    principal_amount: number;
    outstanding_amount: number;
    monthly_due: number;
    last_payment_date: string;
  }>;
  transactions: Array<{
    date: string;
    amount: number;
    type: 'credit' | 'debit';
    description: string;
  }>;
}

export async function getCustomerData(customerId: string): Promise<CustomerData | null> {
  try {
    const response = await fetch(`${API_BASE}/customer/${customerId}`);
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error(`Failed to fetch customer: ${response.statusText}`);
    }
    return response.json();
  } catch {
    return null;
  }
}

export async function saveCustomerData(data: CustomerData): Promise<void> {
  const response = await fetch(`${API_BASE}/admin/customer-data/saveCustomerData`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    throw new Error(`Failed to save customer data: ${response.statusText}`);
  }
}
