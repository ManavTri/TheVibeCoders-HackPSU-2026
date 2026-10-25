export const dashboardStats = [
  {
    title: 'Tuition due',
    value: '$18,420',
    change: '+4.2%',
    detail: 'Compared to last semester',
    tone: 'amber',
    tooltip: 'This is the current semester tuition amount versus the previous billing cycle.',
  },
  {
    title: 'Scholarships',
    value: '$9,750',
    change: '+$1,200',
    detail: 'Awarded and confirmed',
    tone: 'emerald',
    tooltip: 'Confirmed scholarship funding already awarded for this term.',
  },
  {
    title: 'Remaining balance',
    value: '$8,670',
    change: '-$1,480',
    detail: 'After grants and aid',
    tone: 'cyan',
    tooltip: 'This is the outstanding balance after scholarships, grants, and aid are applied.',
  },
  {
    title: 'Monthly budget',
    value: '$2,350',
    change: 'Healthy',
    detail: 'Available for living costs',
    tone: 'violet',
    tooltip: 'This is the monthly cash cushion still available after essential expenses.',
  },
]

export const deadlines = [
  { name: 'Tuition installment', due: 'Due in 4 days', amount: '$4,200', status: 'urgent' },
  { name: 'Housing payment', due: 'Due in 9 days', amount: '$1,350', status: 'watch' },
  { name: 'Scholarship renewal', due: 'Due in 14 days', amount: 'Required form', status: 'normal' },
]

export const warnings = [
  { title: 'Cash flow risk', text: 'You are 12% below your target savings pace for this month.', severity: 'high' },
  { title: 'Document review needed', text: 'Your FAFSA verification packet is still missing one tax transcript.', severity: 'medium' },
  { title: 'Deadline approaching', text: 'The learning support grant requires a signed statement before Friday.', severity: 'low' },
]

export const scholarshipBreakdown = [
  { label: 'Merit grant', value: 42, amount: '$4,100' },
  { label: 'Need-based aid', value: 28, amount: '$2,700' },
  { label: 'Department award', value: 18, amount: '$1,800' },
  { label: 'Other support', value: 12, amount: '$1,150' },
]

export const financialTrends = [
  { month: 'Jan', funding: 3200, expenses: 2900 },
  { month: 'Feb', funding: 3500, expenses: 3050 },
  { month: 'Mar', funding: 3400, expenses: 3250 },
  { month: 'Apr', funding: 4050, expenses: 3450 },
  { month: 'May', funding: 4200, expenses: 3600 },
  { month: 'Jun', funding: 4700, expenses: 3900 },
]

export const documentList = [
  { id: 1, name: '2025 FAFSA Verification.pdf', type: 'Financial aid', updated: '2 hours ago', status: 'Complete' },
  { id: 2, name: 'Spring_2026_Tuition_Invoice.pdf', type: 'Tuition', updated: 'Yesterday', status: 'Awaiting review' },
  { id: 3, name: 'Scholarship_renewal_form.docx', type: 'Scholarship', updated: '3 days ago', status: 'Needs signature' },
  { id: 4, name: 'Bank_statement_July.pdf', type: 'Budget', updated: '1 week ago', status: 'Uploaded' },
]

export const aiMessages = [
  { sender: 'AI', text: 'Your current cash position is on track, but the tuition installment due in 4 days is the biggest upcoming risk.', time: '9:41 AM' },
  { sender: 'You', text: 'Can you suggest the easiest way to reduce my payment gap before the deadline?', time: '9:42 AM' },
  { sender: 'AI', text: 'You could apply your emergency fund and submit the scholarship renewal form this week to offset the balance.', time: '9:43 AM' },
]

export const expenseCategories = [
  { label: 'Housing', value: 28, amount: '$1,900', color: 'bg-[#9bb7a9]', colorValue: '#9bb7a9' },
  { label: 'Food', value: 22, amount: '$1,350', color: 'bg-[#b7c9d9]', colorValue: '#b7c9d9' },
  { label: 'Books', value: 18, amount: '$1,100', color: 'bg-[#d9d7d0]', colorValue: '#d9d7d0' },
  { label: 'Transport', value: 16, amount: '$950', color: 'bg-[#e0c381]', colorValue: '#e0c381' },
  { label: 'Other', value: 16, amount: '$850', color: 'bg-[#c5ced6]', colorValue: '#c5ced6' },
]
