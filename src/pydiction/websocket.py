import time

from typing import Dict, List
from collections import namedtuple

from pydiction.state import State


Subscription = namedtuple("Subscription", ["channels", "tickers", "created_ts", "updated_ts", "active"])


class KalshiWs:

    def __init__(self, state: State) -> None:
        self.state = state
        self.subscriptions: Dict[int, Subscription] = {}
        self._id_counter = 0

    def generate_subscription_id(self) -> int:
        self._id_counter += 1
        return self._id_counter


    def add_subscription(self, channels: List[str]):
        subscription_id = self.generate_subscription_id()
        subscription = Subscription(channels=channels, tickers=self.state.tickers, created_ts=time.time(), updated_ts=time.time(), active=False)

        message = {
            "id": subscription_id,
            "cmd": "subscribe",
            "params": {
                "channels": channels,
                "market_tickers": self.state.tickers
            }
        }

        # TODO: Actually send the request to the ws and handle success/failure
        # TODO: Update the `active` field as well as the `updated_ts`.
        
        # Update the subscription locally
        self.subscriptions[subscription_id] = subscription

        return message

    def update_subscription(self, subscription_id: int, updated_tickers: List[str]):
        """
        Updates a subscription by adding or deleting tickers from it. Infers the correct action.

        - Detects tickers to add by: `tickers_to_add = updated_tickers - current_tickers`
        - Detects tickers to delete by: `tickers_to_delete = current_tickers - updated_tickers`

        Will always update additions before deletions. We assume an addition has higher time priority than a deletion.
        """
        if subscription_id not in self.subscriptions:
            # Exit early
            return []

        subscription = self.subscriptions[subscription_id]
        current_tickers = set(subscription.tickers)
        new_tickers = set(updated_tickers)

        # Determine actions to perform
        tickers_to_add = new_tickers - current_tickers
        tickers_to_delete = current_tickers - new_tickers

        actions_performed = []

        # Create and send addition messages, if any
        if tickers_to_add:
            add_message = {
                "id": self.generate_subscription_id(),
                "cmd": "update_subscription",
                "params": {
                    "sids": [subscription_id],  # presently, support single subscription updates 
                    "market_tickers": list(tickers_to_add),
                    "action": "add_markets"
                }
            }

            # TODO: Actually send the add_message to the ws and handle success/failure

            actions_performed.append("add_markets")

        # Create and send deletion messages, if any
        if tickers_to_delete:
            delete_message = {
                "id": self.generate_subscription_id(),
                "cmd": "update_subscription",
                "params": {
                    "sids": [subscription_id],  # presently, support single subscription updates 
                    "market_tickers": list(tickers_to_delete),
                    "action": "delete_markets"
                }
            }
            
            # TODO: Actually send the delete_message to the ws and handle success/failure

            actions_performed.append("delete_markets")

        # Update the subscription locally
        self.subscriptions[subscription_id] = subscription._replace(tickers=list(new_tickers), updated_ts=time.time())

        return actions_performed

    def unsubscribe(self, subscription_ids: List[int]):
        valid_subscription_ids = [subscription_id for subscription_id in subscription_ids if subscription_id in self.subscriptions]
        
        if valid_subscription_ids:

            unsubscribe_message = {
                "id": self.generate_subscription_id(),
                "cmd": "unsubscribe",
                "params": {
                    "sids": valid_subscription_ids
                }
            }

            # TODO: Actually send the message to the ws and handle success/failure

            # Update subscriptions locally
            for subscription_id in valid_subscription_ids:
                self.subscriptions.pop(subscription_id)

        # TODO: we should return the successfull unsubscribes only
        return valid_subscription_ids

    def resubscribe_all(self):
        """
        Re-subscribes to all active connections after reconnecting.
        """
        for subscription_id, subscription in self.subscriptions.items():
            if subscription.active:
                resubscription_message = {
                    "id": subscription_id,
                    "cmd": "subscribe",
                    "params": {
                        "channels": subscription.channels,
                        "market_tickers": subscription.tickers
                    }
                }

                # Update subscriptions locally
                # NOTE: The logic in only updating the `updated_ts` is that we might want to know just 
                # how long we've been listening to a subscription via the `created_ts`.
                self.subscriptions[subscription_id] = subscription._replace(updated_ts=time.time())


       
if __name__ == '__main__':
    state = State()
    ws = KalshiWs(state)

    ws.add_subscription(["orderbook_delta"])
    print(ws.subscriptions)
    ws.update_subscription(subscription_id=1, updated_tickers=["a", "b", "d"])
    print(ws.subscriptions)
    ws.unsubscribe([1])
    print(ws.subscriptions)
