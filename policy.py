"""
policy.py — QIS-NET Project 2 policy (STUDENT FILE: replace the baseline).

The policy decides, each time a fresh pair arrives on a link, what to do:
swap immediately, purify first, hold, or discard aged pairs. Your variant's
SLOs (rate, fidelity, p95 latency) will typically NOT be met by the
baseline policy below.

Design space (see spec section 3.2):
  * purify while the freshest link fidelity is below a threshold AND a
    second pair is available on the same link;
  * hold vs swap rules (e.g., wait for a purified partner);
  * discard pairs whose current fidelity has fallen below a floor.

AI assistance: Claude (Anthropic) was used to draft and test FreshestCapPolicy.
"""

import math


class BaselinePolicy:
    """Swap-as-soon-as-possible; never purify. PROVIDED as the baseline.
    It meets the reference scenarios' expectations but is deliberately
    insufficient for most variant SLOs."""

    def __init__(self, params):
        self.params = params
        # map each repeater node to its adjacent link pairs for swapping
        self.chains = params["policy"]["swap_chains"]  # list of [left, right]

    def on_pair_ready(self, link, pair, state, sim):
        for left, right in self.chains:
            if state.pairs.get(left) and state.pairs.get(right):
                sim.swap(left, right)


class FreshestCapPolicy:
    """Candidate C: freshest-first swapping with a buffer cap.

    Swap as soon as both sides of a chain hold a pair, always using the
    newest pair on each side (older pairs have decayed further). In each
    chain the faster link (higher attempt_rate * p_success) keeps at most
    `cap` pairs (1, 2 or 4); the oldest are discarded once the cap is
    exceeded, so no stale backlog builds up. A larger cap keeps backup pairs
    for dry spells on the fast link, at the cost of older ones.
    """

    def __init__(self, params, cap=1):
        self.params = params
        self.chains = params["policy"]["swap_chains"]  # list of [left, right]
        self.cap = cap
        rate = [l["attempt_rate"] * l["p_success"] for l in params["topology"]["links"]]
        # per chain: the faster link, whose inventory is capped
        self.fast = [r if rate[r] >= rate[l] else l for l, r in self.chains]

    def on_pair_ready(self, link, pair, state, sim):
        for (left, right), fast in zip(self.chains, self.fast):
            while len(state.pairs.get(fast, [])) > self.cap:
                sim.discard(fast, 0)                       # index 0 = oldest
            if state.pairs.get(left) and state.pairs.get(right):
                sim.swap(left, right,
                         left_index=len(state.pairs[left]) - 1,
                         right_index=len(state.pairs[right]) - 1)


def make_policy(params):
    """Return your policy object. Replace BaselinePolicy with your own class
    (same constructor signature and on_pair_ready hook)."""
    return FreshestCapPolicy(params)
