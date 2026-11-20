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


class FreshestCapPolicy:
    """Freshest-first swap with a buffer cap, structured as discard ->
    purify -> swap. Runs on every new pair, for each swap chain.

    1. Discard: the fast link (higher attempt_rate * p_success) keeps at
       most `cap` pairs; the lowest-fidelity ones go first. The slow link is
       the bottleneck, so its pairs are never discarded.
    2. Purify: only in "purify mode", and only on the fast link while no
       slow-link pair is waiting. Purifies its two pairs (BBPSSW) when the
       result beats the best pair it already has.
    3. Swap: as soon as both links hold a pair, using the best (freshest or
       purified) pair on each side.

    Purify mode is chosen from params and is on only when both hold:
      * fidelity needs help: the expected end-to-end fidelity of a plain
        freshest swap is below the SLO + margin, and
      * memory is good enough for purification to pay off: T2 is at least
        PURIFY_MIN_RATIO x the slow link's mean generation wait. A purified
        pair waits for the next slow-link pair; with shorter memory it
        decays more than purification gains. Measured on variant 13: the
        fidelity gain of purifying is -0.0065 at T2/wait = 1.5, about 0 at
        2.4-3.0 and +0.0066 at 5.9.
    In purify mode the cap is 2 (purification needs two pairs), else 1.
    For variant 13 the two never hold together: at short T2 fidelity needs
    help but purification does not pay off; at long T2 it pays off but is
    not needed. So purify mode stays off and the run is freshest swap, cap 1.
    `purify=True/False` forces the mode for comparison experiments.
    """

    PURIFY_MIN_RATIO = 3.0

    def __init__(self, params, margin=0.01, purify=None):
        self.params = params
        self.chains = params["policy"]["swap_chains"]  # list of [left, right]
        ph = params["physics"]
        t2 = ph["t2_ms"]
        links = params["topology"]["links"]
        rate = [l["attempt_rate"] * l["p_success"] for l in links]  # pairs per ms
        # per chain: the faster link, whose inventory is capped and purified
        self.fast = [r if rate[r] >= rate[l] else l for l, r in self.chains]
        slow_wait = 1.0 / min(rate[l if f == r else r] for (l, r), f in zip(self.chains, self.fast))
        fast_wait = 1.0 / max(rate[f] for f in self.fast)
        # expected fidelity of the newest fast-link pair: its age is
        # exponential with mean fast_wait, so E[exp(-age/T2)] = 1 / (1 + wait/T2)
        keep = 1.0 if math.isinf(t2) else 1.0 / (1.0 + fast_wait / t2)
        f_fast = 0.25 + (ph["f_link"] - 0.25) * keep
        expected = ph["f_link"] * f_fast * ph["f_swap"]
        needs_help = expected < params["slo"]["min_fidelity"] + margin
        pays_off = t2 >= self.PURIFY_MIN_RATIO * slow_wait
        auto = needs_help and pays_off
        self.purify_mode = ph["purification_allowed"] and (auto if purify is None else purify)
        self.cap = 2 if self.purify_mode else 1

    def on_pair_ready(self, link, pair, state, sim):
        for (left, right), fast in zip(self.chains, self.fast):
            slow = left if fast == right else right
            self._discard(state, sim, fast)
            self._purify(state, sim, fast, slow)
            self._swap(state, sim, left, right)

    # -- the three decisions ---------------------------------------------

    def _discard(self, state, sim, fast):
        while len(state.pairs.get(fast, [])) > self.cap:
            sim.discard(fast, self._worst(state, fast))

    def _purify(self, state, sim, fast, slow):
        inv = state.pairs.get(fast, [])
        if not self.purify_mode or len(inv) < 2 or state.pairs.get(slow):
            return                      # a waiting slow-link pair: swap now instead
        # sim.purify uses the two oldest pairs; with cap 2 those are all we hold
        f_low = min(state.current_fidelity(p) for p in inv[:2])
        f_best = max(state.current_fidelity(p) for p in inv)
        if bbpssw(f_low)[0] > f_best:
            sim.purify(fast)

    def _swap(self, state, sim, left, right):
        if state.pairs.get(left) and state.pairs.get(right):
            sim.swap(left, right,
                     left_index=self._best(state, left),
                     right_index=self._best(state, right))

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _best(state, link_id):
        inv = state.pairs[link_id]
        return max(range(len(inv)), key=lambda i: state.current_fidelity(inv[i]))

    @staticmethod
    def _worst(state, link_id):
        inv = state.pairs[link_id]
        return min(range(len(inv)), key=lambda i: state.current_fidelity(inv[i]))


def make_policy(params):
    """Return the graded policy: UltimatePolicy (team's parameterised policy).
    FreshestCapPolicy is kept above as the alternative we compared against."""
    return UltimatePolicy(params)
