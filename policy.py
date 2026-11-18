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

class PurifyThenSwap:
    """Discards pairs whose fidelity is too bad, depending on a threshold and
    if two pairs are available on the fastest link purify the two oldest ones and then swap"""

    def __init__(self, params, purify_link=1, f_purify=1,
                 f_floor=0, max_rounds=1):
        self.params = params
        self.chains = params["policy"]["swap_chains"]  # list of [left, right]
        self.purify_link = purify_link   # link to purify (0 = link 0-1) ||| could have different policies for each link?
        self.f_purify = f_purify         # purify if best pair < f_purify
        self.f_floor = f_floor           # discard all pairs with fidelity < f_floor
        self.max_rounds = max_rounds     # max number of purification per round ||| Right now, only purify once

    def _discard_stale(self, state, sim, link_id):
        inv = state.pairs.get(link_id, [])
        # goes through backwards so that discarding does not change indexes || TO VERIFY IT SEEMS WEIRD
        for i in range(len(inv) - 1, -1, -1):
            if state.current_fidelity(inv[i]) < self.f_floor:
                sim.discard(link_id, i)

    def _maybe_purify(self, state, sim):
        inv = state.pairs.get(self.purify_link, [])
        rounds = 0
        while (rounds < self.max_rounds and len(inv) >= 2 and max(state.current_fidelity(p) for p in inv) < self.f_purify):
            sim.purify(self.purify_link)
            rounds += 1

    def on_pair_ready(self, link, pair, state, sim):
        for left, right in self.chains:
            self._discard_stale(state, sim, left)
            self._discard_stale(state, sim, right)
            self._maybe_purify(state, sim)
            # swap most recent pairs (index -1 = most recent)
            while state.pairs.get(left) and state.pairs.get(right):
                sim.swap(left, right, left_index=-1, right_index=-1)

def make_policy(params):
    """Return your policy object. Replace BaselinePolicy with your own class
    (same constructor signature and on_pair_ready hook)."""
    return PurifyThenSwap(params)
