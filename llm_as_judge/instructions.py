judge_prompt = '''
You are a judge tasked with evaluating a **trimmed routine** that has been customized for a customer.

You will score the routine using the official **trimming rubric**. You will receive:
1. CUSTOMER DATA (used for trimming)
2. The FULL ORIGINAL ROUTINE
3. The TRIMMED ROUTINE
4. The TRIMMING INSTRUCTIONS the author followed

---

## Important Evaluation Principles

**Only penalize missing steps if they were:**
- Tool calls or logic required for **this customer's data**
- **Not already resolved and expressed directly in the trimmed text**

It is **correct** to:
- **Inline results** from tools like `get_billing_info`, `check_account_status`, `evaluate_payment_urgency`, etc.
- Omit `_extra` tools and irrelevant logic paths
- Terminate all steps after `complete_case(...)` in a branch

 Do **not** penalize for:
- Replacing tool calls with direct values from customer data
- Skipping irrelevant branches for other user types
- Omitting logic that occurs **after** a terminal tool like `complete_case(...)`

---

## What You Are Scoring

### 1. Relevance
Does the trimmed routine include **only** steps relevant to this customer, based on their data?

- **5** = Only logic relevant to the customer remains
- **4** = One minor irrelevant step or fallback remains
- **3** = A few irrelevant branches or tool calls remain
- **2** = Several unnecessary or mismatched steps remain
- **1** = Most of the logic still applies to other scenarios

**Relevance Pitfalls to Watch For:**
- Keeping `_extra` tool calls
- Keeping multiple conditional branches where the customer data clearly selects one
- Including logic after a `complete_case(...)` that should have terminated the routine

---

### 2. Completeness
Did the trimmed routine keep **all necessary logic**, tools, and branches that apply to this customer?

- **5** = Everything required for this customer is preserved
- **4** = One small required step or message is missing
- **3** = A few required paths or tools are missing
- **2** = A major tool or path was skipped
- **1** = The routine drops essential logic

**Completeness Pitfalls to Watch For:**
- Skipping tool calls that are not resolved by data (e.g. `calculate_patient_responsibility(...)`)
- Omitting success/failure branches for conditionally executed tools
- Failing to include steps that were **still relevant** for this customer, even if they come after a `yes` response
- Steps not reachable due to known early exit conditions (e.g. suspended account) should NOT be counted as “missing” in the completeness score.
---

### How to Explain Your Scores

For each score, explain:
- **What was correct** (briefly)
- **If not a 5**, what step or branch caused the deduction and **why it was wrong**
- Use phrases like “This step should have been pruned because the customer data shows…” or “This tool call was required because…”

Example (Relevance Score = 4):  
> “The step calling `get_billing_info_extra(...)` was retained even though all its outputs are present in the customer data. This should have been replaced with inlined values.”

---

## Your Task

Compare the FULL ROUTINE and TRIMMED ROUTINE using the CUSTOMER DATA and TRIMMING INSTRUCTIONS.

**CRITICAL JSON FORMAT REQUIREMENTS:**

1. **Return ONLY valid JSON** - no markdown, no code blocks, no extra text
2. **Use exactly these 4 fields** with these exact names:
   - `relevance_score`: string with value "1", "2", "3", "4", or "5"
   - `relevance_explanation`: string explaining your relevance score
   - `completeness_score`: string with value "1", "2", "3", "4", or "5" 
   - `completeness_explanation`: string explaining your completeness score
3. **Escape quotes properly** - use \\" for quotes within string values
4. **No trailing commas** - ensure the last field doesn't have a comma
5. **Single-level structure** - do NOT nest JSON objects

**CORRECT JSON EXAMPLE:**
{
  "relevance_score": "5",
  "relevance_explanation": "All branches and tool calls irrelevant to this customer were correctly removed. The customer data shows they have an \\"active\\" account, so suspended account logic was properly pruned.",
  "completeness_score": "4",
  "completeness_explanation": "Most required logic was preserved, but the success branch for payment processing was missing one confirmation step that should have been retained."
}

Now evaluate the trimmed routine and return your response as valid JSON with exactly the 4 required fields.

===== CUSTOMER DATA =====
CUSTOMER_DATA

===== FULL ROUTINE =====
FULL_ROUTINE

===== TRIMMED ROUTINE =====
TRIMMED_ROUTINE
'''