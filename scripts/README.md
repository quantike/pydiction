# Scripts

The `/scripts` directory is a collection of one-off scripts that are prediction market trading helpers. The intention is that these scripts are ran as CLIs (typically using [fire](https://github.com/google/python-fire)).

## Kelly

Simple [Kelly Criterion](https://en.wikipedia.org/wiki/Kelly_criterion) script that will calculate the sizing for a sequence of bets which maximizes the long-term expected value of the logarithm of wealth.

```sh
uv run kelly.py bet
    --side="NO"       # which side of the bet you're on
    --ps=25           # subjective probability (think in ps=100-expected)
    --k=64            # strike price for contract
    --bankroll=86.71  # current wealth in dollars
    --kelly=0.5       # for fractional Kelly
    --is_bid=False    # going short or selling?
```
