from collections import namedtuple


Subscription = namedtuple(
    "Subscription", ["channels", "tickers", "created_ts", "updated_ts", "active"]
)
