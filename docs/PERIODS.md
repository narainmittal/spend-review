# Reporting periods

Set `period` in your private configuration to one of these objects. All endpoints are inclusive and use transaction dates, not statement dates. No year or index is inferred.

| Frequency | Configuration | Resolved dates |
| --- | --- | --- |
| Monthly | `{"frequency":"monthly","year":2032,"month":2}` | 2032-02-01 to 2032-02-29 |
| Quarterly | `{"frequency":"quarterly","year":2030,"quarter":3}` | 2030-07-01 to 2030-09-30 |
| Half-yearly | `{"frequency":"half-yearly","year":2030,"half":2}` | 2030-07-01 to 2030-12-31 |
| Yearly | `{"frequency":"yearly","year":2030}` | 2030-01-01 to 2030-12-31 |
| Custom | `{"frequency":"custom","start":"2030-04-06","end":"2031-04-05"}` | Exactly the supplied dates |

Existing configurations with only `start` and `end` remain supported as custom periods. Presets are calendar-based, not a guess about your country's fiscal year. Use custom dates for fiscal years, rolling windows or non-calendar half-years. Explicit dates that conflict with a preset are rejected. Initialization writes the resolved endpoints alongside the preset.

The same review, coverage and reconciliation requirements apply to every frequency. A longer reporting window may need more source statements, including boundary statements. Changing dates requires rechecking reviews and coverage approvals; previous approval is not evidence for a newly added month. Reports use `spending-summary.md` and `period_total` regardless of frequency.
