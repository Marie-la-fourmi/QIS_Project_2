"""
policy.py — QIS-NET Project 2 policy.

AI assistance: OpenAI Codex helped implement freshest-first swapping and the fidelity threshold.

The policy decides, each time a fresh pair arrives on a link, what to do:
swap immediately, purify first, hold, or discard aged pairs. Your variant's
SLOs (rate, fidelity, p95 latency) guide the choice of policy.

Design space (see spec section 3.2):
  * purify while the freshest link fidelity is below a threshold AND a
    second pair is available on the same link;
  * hold vs swap rules (e.g., wait for a purified partner);
  * discard pairs whose current fidelity has fallen below a floor.
"""

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


class FreshestFirstPolicy:
    """Swap the newest pairs when their predicted output meets the threshold."""

    def __init__(self, params, min_swap_fidelity=0.0):
        self.chains = params["policy"]["swap_chains"]
        self.min_swap_fidelity = min_swap_fidelity

    def on_pair_ready(self, link, pair, state, sim):
        for left, right in self.chains:
            left_pairs = state.pairs.get(left)
            right_pairs = state.pairs.get(right)
            if not left_pairs or not right_pairs:
                continue

            predicted_fidelity = (
                state.current_fidelity(left_pairs[-1])
                * state.current_fidelity(right_pairs[-1])
                * state.f_swap
            )
            if predicted_fidelity >= self.min_swap_fidelity:
                sim.swap(left, right, left_index=-1, right_index=-1)


def make_policy(params):
    """Return freshest-first swapping with a 0.80 output fidelity threshold."""
    return FreshestFirstPolicy(params, min_swap_fidelity=0.80)
