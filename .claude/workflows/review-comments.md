# /review-comments - Address PR Review Comments

Do not blindly implement AI suggestions.

1. Identify the PR.
2. Fetch PR conversation, reviews, and inline comments.
3. For each finding, read the referenced code.
4. Classify each finding:
   - Valid bug or repo-rule violation: fix.
   - False positive: dismiss with evidence.
   - Already fixed: note commit.
   - Style-only: skip unless requested.
   - Product-scope change: defer unless approved.
5. Fix confirmed issues only.
6. Run targeted tests and smoke checks as needed.
7. Commit and push.
8. Report reviewer, findings, fixed count, dismissed count, deferred count, and notes.
