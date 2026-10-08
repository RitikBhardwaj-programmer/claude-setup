# The moves outside physics

The videos are all physics and maths. This table carries each move into other fields. These mappings are inferred, not observed in the videos.

| Move | CS / coding | Networking | Maths / exam prep |
|---|---|---|---|
| Reject the label | "Use an index because it is faster": faster how? Show the tree walk vs the table scan. | "TCP is reliable": what exactly must the protocol do to be reliable? | "Apply L'Hôpital": why does comparing rates settle 0/0? |
| Rediscover, don't recall | Re-derive the 3-way handshake: what fails with one message? With two? | Build "address = network part + host part" before naming subnet masks. | Rebuild the geometric series sum from n = 1, 2, 3. |
| Naive model, then break it | "More threads, more speed": breaks on lock contention. | "Send faster": breaks on congestion → fixed window → AIMD (additive increase, multiplicative decrease). | "Probability of A or B = P(A) + P(B)": breaks on overlap. |
| Tinker one variable | Double the input to a nested loop: time grows ×4, not ×2. | Double bandwidth and packet size: which effect on transfer time cancels? | Push a parameter to 0 and ∞ to see the shape of a function. |
| Demand the mechanism | Explain a throughput cap by following one request through every queue. | Head-of-line blocking: watch one stuck packet hold back the rest. | Why does the derivative of eˣ equal eˣ? Look at what "growth proportional to size" means. |
| Reframe / easier twin | "Can these deadlock?" becomes "does the wait-for graph have a cycle?" | Study one congested link before the whole network. | Prove for n = 1, 2 by hand before the general case. |
| Hold the invariant | Fix "no reader sees a half-written row": what locking must then exist? | Fix "bytes arrive in order": what must give? (buffering, retransmission) | List the invariants of a B-tree or heap, then deduce where a new key goes. |
| Define the word / count | Decide what "pure function" means exactly before judging a case. | Does "bandwidth" mean capacity or achieved throughput? | "How good is this hash?" becomes "how many keys per bucket?" |
| Spot the coincidence | Two services fail at the same minute each night: look for a shared cron job. | One latency spike in two unrelated paths points to a shared dependency. | O(log n) in heaps and in binary search: both come from halving. |
| Limits / special cases | A cost formula must reduce to the known case at n = 1. | Check a subnet formula on /32 and /0. | Check a recurrence on n = 2 and n = 3; check units. |
| Two ledgers | Balance from the transaction log vs from the snapshot. | Count packets at the sender and at the receiver; the difference locates the drop. | Solve the same problem two ways (algebra and diagram). |
| Decisive test | "Server overloaded or network slow?": design the test that only one cause passes. | Send a keepalive to test whether the connection is alive. | Find one counterexample that would kill a conjecture. |
| Cause audit | The test passes after the change: was it the change, or a warm cache? | Latency improved after the route change: was it the change, or lower traffic that hour? | A right answer from a wrong method still costs marks: check the reasoning. |
| Try to break it / widen the boundary | A cache "creates" speed until you count the memory and invalidation cost. | Try to beat a rate limiter with parallel clients: find the hidden counter. | "Free energy" puzzles: find the term you left out. |
| One picture, many results | One cache-line diagram explains false sharing, prefetching and stride effects. | One sequence diagram answers every timeout question. | The unit circle gives the identities, the derivatives and the phase. |

## Exam-prep use
For a GATE-style topic, run **explain** mode, then end with 2–3 practice questions that test the *why*. A good question asks what changes if a variable is doubled, or which assumption a formula depends on, not just plugging in numbers.
