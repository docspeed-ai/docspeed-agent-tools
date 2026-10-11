# How to check document answers for completeness

A document answer can cite the right passage and still leave out something your application needs. In a recorded Docspeed test across two synthetic agreements, every returned citation pointed to a supporting passage on the correct document and page. The first answer still omitted who had to pay a termination fee and when it was due. The evaluation remained a partial result.

For developers building document features, this creates two separate checks: does the source support what the answer says, and does the answer cover what the task requested?

The [two-agreement example](https://api.docspeed.ai/agent-tools/examples/two-contracts/) makes the distinction inspectable. Alpha requires at least 30 calendar days of written notice; Beta requires at least 60. Alpha also states a USD 500 early termination fee when termination occurs before 31 October 2027. The recorded answer identified those terms, and the follow-up correctly distinguished Beta’s silence about a fee from an explicit waiver.

But the first answer did not explicitly identify the terminating party as the payer or say that payment was due on the termination date. Both details were inside the returned fee citation. A valid citation therefore did not satisfy the full acceptance criteria. The public example preserves the actual answers and all six returned source regions, including the incomplete answer. This was an internal direct API evaluation on 11 October 2026, with two synthetic PDFs, two Ask calls and no retries.

Structured extraction has a similar distinction between a correct value and a useful representation. The [recorded invoice extraction](https://api.docspeed.ai/agent-tools/examples/source-review/) exposes eleven header fields and fifteen line-item cells alongside their source boxes. An offline review checked all 26 values against the text inside those boxes. The printed freight amount was `0.00`, returned as numeric `0.0`. Those representations agree; neither should be treated as a missing value. This was one recorded internal native Codex run on 10 October 2026, under explicit per-run MCP configuration. It does not establish current installation readiness or accuracy on other invoices.

A separate [invoice question and follow-up](https://api.docspeed.ai/agent-tools/examples/cited-qa/) shows another review boundary. Both recorded answers identify the invoice number and USD 1,250.00 amount due, with source areas for each. The saved follow-up reused the returned session and the same ordered inputs. That establishes continuity in the recorded requests; it does not prove that parsing or indexing was skipped. These answers came from an internal MCP acceptance suite, not a recorded Codex or Claude conversation.

An application evaluation can make these boundaries explicit before a run. Define the required fields or propositions, including roles, dates, units and the treatment of missing information. Check each returned citation against the correct document and page. Then check the answer independently for completeness. A fee amount without its payer or due date can remain incomplete even when its source box contains all three.

Absence needs its own review: a passage that does not mention a fee cannot alone establish that the entire agreement contains no fee clause. In the two-agreement evaluation, the absence judgment was checked against the whole one-page Beta source. Longer documents require a correspondingly broader check.

These examples offer inspectable historical results, not a general accuracy benchmark, customer case study or evidence of cost savings. They use clean synthetic documents. Scans, handwriting, conflicting clauses, larger document sets and real application workloads would need separate evaluation. The [Codex and Claude Code setup guide](https://api.docspeed.ai/agent-tools/) provides the integration instructions; the examples provide concrete material for deciding what a result must contain before an application accepts it.

*Prepared with AI assistance from Docspeed’s retained internal test artifacts and source reviews. No customer documents were used in these examples.*
