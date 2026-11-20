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

class UltimatePolicy:
    def __init__(self, params, f_purify1=1, f_purify0=1,
                 f_floor0=0, f_floor1=0, max_rounds0=1, max_rounds1=1):   #all the parameters we can act on
        self.params = params
        self.chains = params["policy"]["swap_chains"]  # list of [left, right]
        self.f_purify = (f_purify0, f_purify1)  # purify if best pair < f_purify
        self.f_floor = (f_floor0, f_floor1)    # discard all pairs with fidelity < f_floor
        self.max_rounds = (max_rounds0, max_rounds1) # max number of purification per round ||| Right now, only purify once

    def _discard_stale(self, state, sim, link_id, floor):
        inv = state.pairs.get(link_id, [])
        for i in range(len(inv) - 1, -1, -1):
            if state.current_fidelity(inv[i]) < floor:
                sim.discard(link_id, i)

    def _maybe_purify(self, state, sim, link_id, threshold, max_rounds):
        inv = state.pairs.get(link_id, [])   # même liste que sim.purify modifie
        rounds = 0
        while (rounds < max_rounds and len(inv) >= 2
               and max(state.current_fidelity(p) for p in inv) < threshold):
            sim.purify(link_id)
            rounds += 1

    def on_pair_ready(self, link, pair, state, sim):
        for left, right in self.chains:
            links = (left, right)
            for side, lid in enumerate(links):
                self._discard_stale(state, sim, lid, self.f_floor[side])
                self._maybe_purify(state, sim, lid,
                                   self.f_purify[side], self.max_rounds[side])  
            while state.pairs.get(left) and state.pairs.get(right):
                sim.swap(left, right, left_index=-1, right_index=-1) #currently switches the freshest ones, change the indexes if needed
                #actually purify puts its new pair at the beginning of the list so -1 is not necessarly the best one !!!!!


def make_policy(params):
    """Return the graded policy: UltimatePolicy (team's parameterised policy).
    No purification; discard link-1 pairs that have decayed below 0.913, then
    swap the freshest pairs. FreshestCapPolicy is kept above as the alternative
    we compared against."""
    return UltimatePolicy(params, f_purify0=0, f_purify1=0, f_floor1=0.913)
