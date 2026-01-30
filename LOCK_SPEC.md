# Income Strategy Engine — LOCK SPEC
Version: 1.0 (LOCKED)

==================================================
GLOBAL RULES (NON-NEGOTIABLE)
==================================================
1. NO tab may be removed, hidden, or renamed.
2. NO section may be removed unless explicitly approved.
3. All dollar values:
   - Positive → GREEN
   - Negative → RED
4. Strategy logic must be explainable and visible.
5. News summaries must be analytical, not headline copies.

==================================================
REQUIRED TABS (MUST ALWAYS EXIST)
==================================================
- Dashboard
- Strategy
- News
- Portfolio
- Snapshots

==================================================
STRATEGY TAB — REQUIRED SECTIONS (A–E)
==================================================
A. Combined Signal Table
   - 14d price ($)
   - 28d price ($)
   - Monthly income ($)
   - Distribution stability (with logic)
   - News sentiment
   - Final signal

B. Distribution Stability Analysis
   - Income vs price damage (numbers shown)

C. Market / Regime Banner
   - Constructive / Mixed / Risk-Off
   - Visible at top of Strategy tab

D. Do Nothing Day Rule
   - Triggered by regime-driven moves
   - Explicit warning shown

E. Momentum & Trade Bias
   - 14d vs 28d interpretation
   - Integrated with regime

==================================================
PORTFOLIO TAB — REQUIRED SECTIONS (F–I)
==================================================
F. Shares input
G. Dividend per share
H. Total dividend per ETF (weekly / monthly / annual)
I. Position value

==================================================
NEWS TAB — REQUIRED SECTIONS
==================================================
1. Market / Sector / ETF status banner
2. THREE AI-generated analytical summaries
3. Full headline lists below summaries

==================================================
SNAPSHOTS TAB — REQUIRED
==================================================
- Save snapshot
- Historical portfolio value chart