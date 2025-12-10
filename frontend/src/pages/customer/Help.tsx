import { useState } from 'react';
import { HelpCircle, Send, MessageSquare, FileText, Phone, Mail, CheckCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/contexts/AuthContext';
import { useNotifications } from '@/contexts/NotificationContext';
import { useToast } from '@/hooks/use-toast';

const faqs = [
  {
    question: 'How is my loan eligibility determined?',
    answer: 'Your eligibility is determined by 11 rules covering income, account age, payment history, credit usage, and more. You need to satisfy at least 8 rules for review or all 11 for approval.'
  },
  {
    question: 'What documents do I need for a loan?',
    answer: 'Our AI agent automatically fetches your bank statements and credit profile. No additional documents are required for the initial eligibility check.'
  },
  {
    question: 'How long does the decision process take?',
    answer: 'The initial eligibility check is instant. If your application goes to review, an admin will assess it within 1-2 business days.'
  },
  {
    question: 'Can I appeal a rejected application?',
    answer: 'Yes, you can message the admin through this Help section to discuss your application and request a re-evaluation.'
  }
];

export default function CustomerHelp() {
  const { user } = useAuth();
  const { addNotification } = useNotifications();
  const { toast } = useToast();
  
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) return;

    setIsSubmitting(true);
    
    // Simulate sending message to admin
    setTimeout(() => {
      addNotification(
        user?.name || 'Customer',
        user?.customerId || 'Unknown',
        `Subject: ${subject}\n\n${message}`
      );
      
      toast({
        title: 'Message sent',
        description: 'Your message has been sent to the admin team.'
      });
      
      setSubject('');
      setMessage('');
      setSubmitted(true);
      setIsSubmitting(false);
      
      setTimeout(() => setSubmitted(false), 3000);
    }, 1000);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card">
        <h2 className="font-semibold text-foreground">Help & Support</h2>
        <p className="text-sm text-muted-foreground">Get help or contact the admin team</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 scrollbar-thin space-y-6">
        {/* Contact Admin */}
        <section>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Contact Admin
          </h3>
          <Card className="p-4">
            {submitted ? (
              <div className="flex flex-col items-center justify-center py-8 text-center animate-fade-in">
                <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center mb-3">
                  <CheckCircle className="w-6 h-6 text-success" />
                </div>
                <h4 className="font-medium text-foreground mb-1">Message Sent!</h4>
                <p className="text-sm text-muted-foreground">
                  We'll get back to you soon.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">
                    Subject
                  </label>
                  <Input
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="e.g., Question about my loan decision"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">
                    Message
                  </label>
                  <Textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Describe your question or concern..."
                    rows={4}
                  />
                </div>
                <Button type="submit" disabled={isSubmitting || !subject.trim() || !message.trim()}>
                  <Send className="w-4 h-4 mr-2" />
                  {isSubmitting ? 'Sending...' : 'Send Message'}
                </Button>
              </form>
            )}
          </Card>
        </section>

        {/* FAQs */}
        <section>
          <h3 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Frequently Asked Questions
          </h3>
          <div className="space-y-3">
            {faqs.map((faq, idx) => (
              <Card key={idx} className="p-4">
                <h4 className="font-medium text-foreground mb-2 flex items-start gap-2">
                  <HelpCircle className="w-4 h-4 mt-0.5 text-primary flex-shrink-0" />
                  {faq.question}
                </h4>
                <p className="text-sm text-muted-foreground pl-6">{faq.answer}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* Contact Info */}
        <section>
          <h3 className="text-sm font-medium text-muted-foreground mb-3">Other Ways to Reach Us</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Card className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Phone className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Phone</p>
                <p className="font-medium text-foreground">1800-123-4567</p>
              </div>
            </Card>
            <Card className="p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Mail className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                <p className="font-medium text-foreground">support@bankagent.com</p>
              </div>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}
