# Flow summary/ admin control
- Normal flow: user starts checkout → Stripe creates subscription → webhook invoice.payment_succeeded marks local Subscription active and (optionally) records payment/transaction → affiliate distribution runs automatically.

- Manual bank-transfer flow: create
Subscription with pending_approval=True and status pending; admin (or script) marks approved which sets pending_approval=False and then record payment & call aff_utils.distribute_commissions to pay uplines.

- Allow users to request payout of their affiliate commission: model a PayoutRequest pointing to user and amount, admin approves and you create a Transaction and reduce CompanyRevenue / mark Commission paid.
