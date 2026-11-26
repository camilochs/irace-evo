"""Randomised greedy for the 0/1 knapsack problem.

Each restart adds items in an order biased by score(): at every step it
picks among the `alpha` share of best-scored items that still fit. Prints
the best total value found, which irace-evo turns into a cost.

    python3 knapsack.py -i instance.txt --alpha 0.3 --restarts 20 --seed 1
"""
import argparse
import random


def score(value, weight, capacity_left):
    """How attractive an item is; the function irace-evo may rewrite."""
    return value / weight


def construct(items, capacity, alpha, rng):
    left, total, chosen = capacity, 0, set()
    while True:
        fits = [i for i, (v, w) in enumerate(items) if i not in chosen and w <= left]
        if not fits:
            return total
        fits.sort(key=lambda i: score(items[i][0], items[i][1], left), reverse=True)
        pick = rng.choice(fits[: max(1, int(alpha * len(fits)))])
        chosen.add(pick)
        left -= items[pick][1]
        total += items[pick][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", required=True)
    ap.add_argument("--alpha", type=float, default=0.3)
    ap.add_argument("--restarts", type=int, default=20)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    with open(a.i) as f:
        n, capacity = map(int, f.readline().split())
        items = [tuple(map(int, f.readline().split())) for _ in range(n)]
    rng = random.Random(a.seed)
    print(max(construct(items, capacity, a.alpha, rng) for _ in range(a.restarts)))


if __name__ == "__main__":
    main()
