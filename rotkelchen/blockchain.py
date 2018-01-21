from gevent.lock import Semaphore
from urllib.request import Request, urlopen

from rotkelchen.ethchain import Ethchain
from rotkelchen.fval import FVal
from rotkelchen.utils import cache_response_timewise


class Blockchain(object):

    def __init__(
            self,
            blockchain_accounts,
            all_eth_tokens,
            owned_eth_tokens,
            inquirer,
            ethrpc_port
    ):
        self.lock = Semaphore()
        self.results_cache = {}
        self.ethchain = Ethchain(ethrpc_port)
        self.inquirer = inquirer
        self.accounts = blockchain_accounts
        self.all_eth_tokens = all_eth_tokens
        self.owned_eth_tokens = owned_eth_tokens
        self.balances = {}
        self.totals = {}

    @cache_response_timewise()
    def query_balances(self):
        self.query_ethereum_balances()
        self.query_btc_balances()
        return {'per_account': self.balances, 'totals': self.totals}

    def query_btc_balances(self):
        if 'BTC' not in self.accounts:
            return

        self.balances['BTC'] = {}
        btc_usd_price = self.inquirer.find_usd_price('BTC')
        total = FVal(0)
        for account in self.accounts['BTC']:
            btc_resp = urlopen(Request(
                'https://blockchain.info/q/addressbalance/%s' % account
            ))

            balance = FVal(btc_resp.read()) * FVal('0.00000001')  # result is in satoshis
            total += balance
            self.balances['BTC'][account] = {'amount': balance, 'usd_value': balance * btc_usd_price}

        self.totals['BTC'] = {'amount': total, 'usd_value': total * btc_usd_price}

    def query_ethereum_balances(self):
        if 'ETH' not in self.accounts:
            return

        eth_accounts = self.accounts['ETH']
        eth_usd_price = self.inquirer.find_usd_price('ETH')
        balances = self.ethchain.get_multieth_balance(eth_accounts)
        eth_total = FVal(0)
        eth_balances = {}
        for account, balance in balances.items():
            eth_total += balance
            eth_balances[account] = {'ETH': balance, 'usd_value': balance * eth_usd_price}

        self.totals['ETH'] = {'amount': eth_total, 'usd_value': eth_total * eth_usd_price}

        # And now for tokens
        tokens_to_check = None
        if len(self.owned_eth_tokens) > 0:
            tokens_to_check = self.owned_eth_tokens

        token_balances = {}
        token_usd_price = {}
        for token in self.all_eth_tokens:
            try:
                token_symbol = str(token['symbol'])
            except (UnicodeDecodeError, UnicodeEncodeError):
                # skip tokens with problems in unicode encoding decoding
                continue
            if tokens_to_check and token_symbol not in tokens_to_check:
                continue

            usd_price = self.inquirer.find_usd_price(token_symbol)
            if usd_price == 0:
                # skip tokens that have no price
                continue
            token_usd_price[token_symbol] = usd_price

            token_balances[token_symbol] = self.ethchain.get_multitoken_balance(
                token_symbol,
                token['address'],
                token['decimal'],
                eth_accounts,
            )

        for token, token_accounts in token_balances.items():

            # self.totals[token] = FVal(0)
            token_total = FVal(0)
            for account, balance in token_accounts.items():
                token_total += balance
                usd_value = balance * token_usd_price[token]
                if account not in eth_balances:
                    import pdb
                    pdb.set_trace()
                eth_balances[account][token] = balance
                eth_balances[account]['usd_value'] = eth_balances[account]['usd_value'] + usd_value

            self.totals[token] = {'amount': token_total, 'usd_value': token_total * token_usd_price[token]}

        self.balances['ETH'] = eth_balances
