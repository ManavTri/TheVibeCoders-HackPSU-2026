alter table public.documents
  drop constraint if exists documents_type_check;

alter table public.documents
  add constraint documents_type_check
  check (
    type in (
      'award_letter',
      'tuition_bill',
      'financial_aid_package',
      'study_abroad_quote',
      'loan_offer',
      'payment_plan',
      'housing_contract',
      'other'
    )
  );
