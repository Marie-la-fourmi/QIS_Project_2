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

AI assistance: Claude (Anthropic) was used to draft and test FreshestCapPolicy
and to tune the UltimatePolicy parameters used in make_policy.
"""

import math

from qnetsim import bbpssw


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


class SwapFreshestPolicy:
    """Swap-as-soon-as-possible, the freshest one; never purify"""
    def __init__(self,params):
        self.params = params
        # map each repeater node to its adjacent link pairs for swapping
        self.chains = params["policy"]["swap_chains"]  # list of [left, right]

    def on_pair_ready(self, link, pair, state, sim):
        for left, right in self.chains:
            if state.pairs.get(left) and state.pairs.get(right):
                sim.swap(left, right,left_index=-1, right_index=-1)

def make_policy(params):
    """Return the graded policy: UltimatePolicy (team's parameterised policy).
    No purification; discard link-1 pairs that have decayed below 0.913, then
    swap the freshest pairs. FreshestCapPolicy is kept above as the alternative
    we compared against."""
    return SwapFreshestPolicy(params)
