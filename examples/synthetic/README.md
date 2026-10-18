# Synthetic demo

Every name, date, transaction, approval and amount in this folder is invented from scratch. It is not a redacted personal dataset. Never replace these fixtures with real statements.

Expected recorded spending: bank 100.00 + card 1,050.00 + separate EMI 200.00 = **1,350.00 USD**. The store aggregate is 550.00 after its confirmed 50.00 return, so it exceeds the 500.00 major threshold even though its individual charges do not. A separate payee at exactly 500.00 is omitted. The bank purchase at exactly the 100.00 review threshold needs no high-value review. The April row contributes zero. The unmatched credit 5.00 remains separate. Eight required review decisions are fictional approvals for testing only.

Monthly combined spending: January 400.00, February 250.00, March 700.00. Special reviews are subsets of the same ledger and are not additional expenses.

Run read-only validation directly. Copy this directory into ignored `data/demo/` before generating reports or changing decisions.
