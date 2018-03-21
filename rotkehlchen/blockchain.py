import operator
from collections import defaultdict

from gevent.lock import Semaphore
from urllib.request import Request, urlopen

from rotkehlchen.errors import InputError
from rotkehlchen.ethchain import Ethchain
from rotkehlchen.fval import FVal
from rotkehlchen.utils import cache_response_timewise

import logging
logger = logging.getLogger(__name__)


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
        self.owned_eth_tokens = owned_eth_tokens

        # All the known tokens, along with addresses and decimals
        self.all_eth_tokens = {}
        for token in all_eth_tokens:
            try:
                token_symbol = str(token['symbol'])
            except (UnicodeDecodeError, UnicodeEncodeError):
                # skip tokens with problems in unicode encoding decoding
                continue

            self.all_eth_tokens[token_symbol] = {
                'address': token['address'],
                'decimal': token['decimal']
            }
        # Per account balances
        self.balances = defaultdict(dict)
        # Per asset total balances
        self.totals = defaultdict(dict)

    @property
    def eth_tokens(self):
        return self.owned_eth_tokens

    @cache_response_timewise()
    def query_balances(self):
        self.query_ethereum_balances()
        self.query_btc_balances()
        return {'per_account': self.balances, 'totals': self.totals}

    def query_btc_account_balance(self, account):
        btc_resp = urlopen(Request(
            'https://blockchain.info/q/addressbalance/%s' % account
        ))
        return FVal(btc_resp.read()) * FVal('0.00000001')  # result is in satoshis

    def query_btc_balances(self):
        if 'BTC' not in self.accounts:
            return

        self.balances['BTC'] = {}
        btc_usd_price = self.inquirer.find_usd_price('BTC')
        total = FVal(0)
        for account in self.accounts['BTC']:
            balance = self.query_btc_account_balance(account)
            total += balance
            self.balances['BTC'][account] = {'amount': balance, 'usd_value': balance * btc_usd_price}

        self.totals['BTC'] = {'amount': total, 'usd_value': total * btc_usd_price}

    def track_new_tokens(self, tokens):
        intersection = set(tokens).intersection(set(self.owned_eth_tokens))
        if intersection != set():
            raise InputError('Some of the new provided tokens to track already exist')

        self.owned_eth_tokens.extend(tokens)
        self.query_ethereum_tokens(tokens, self.balances['ETH'])
        return {'per_account': self.balances, 'totals': self.totals}

    def remove_eth_tokens(self, tokens):
        for token in tokens:
            usd_price = self.inquirer.find_usd_price(token)
            for account, account_data in self.balances['ETH'].items():
                if token not in account_data:
                    continue

                balance = account_data[token]
                deleting_usd_value = balance * usd_price
                del self.balances['ETH'][account][token]
                self.balances['ETH'][account]['usd_value'] = (
                    self.balances['ETH'][account]['usd_value'] -
                    deleting_usd_value
                )

            del self.totals[token]
            self.owned_eth_tokens.remove(token)

        return {'per_account': self.balances, 'totals': self.totals}

    def modify_btc_account(self, account, append_or_remove, add_or_sub):
        """Either appends or removes a BTC acccount.

        Call with 'append', operator.add to add the account
        Call with 'remove', operator.sub to remove the account
        """
        getattr(self.accounts['BTC'], append_or_remove)(account)
        btc_usd_price = self.inquirer.find_usd_price('BTC')
        balance = self.query_btc_account_balance(account)
        usd_balance = balance * btc_usd_price
        if append_or_remove == 'append':
            self.balances['BTC'][account] = {'amount': balance, 'usd_value': usd_balance}
        elif append_or_remove == 'remove':
            del self.balances['BTC'][account]
        else:
            raise ValueError('Programmer error: Should be append or remove')
        self.totals['BTC']['amount'] = add_or_sub(self.totals['BTC'].get('amount', 0), balance)
        self.totals['BTC']['usd_value'] = add_or_sub(
            self.totals['BTC'].get('usd_value', 0),
            usd_balance
        )

    def modify_eth_account(self, account, append_or_remove, add_or_sub):
        """Either appends or removes an ETH acccount.

        Call with 'append', operator.add to add the account
        Call with 'remove', operator.sub to remove the account
        """
        getattr(self.accounts['ETH'], append_or_remove)(account)
        eth_usd_price = self.inquirer.find_usd_price('ETH')
        balance = self.ethchain.get_eth_balance(account)
        usd_balance = balance * eth_usd_price
        if append_or_remove == 'append':
            self.balances['ETH'][account] = {'ETH': balance, 'usd_value': usd_balance}
        elif append_or_remove == 'remove':
            del self.balances['ETH'][account]
        else:
            raise ValueError('Programmer error: Should be append or remove')
        self.totals['ETH']['amount'] = add_or_sub(self.totals['ETH'].get('amount', 0), balance)
        self.totals['ETH']['usd_value'] = add_or_sub(
            self.totals['ETH'].get('usd_value', 0),
            usd_balance
        )

        for token in self.owned_eth_tokens:
            usd_price = self.inquirer.find_usd_price(token)
            if usd_price == 0:
                # skip tokens that have no price
                continue

            token_balance = self.ethchain.get_token_balance(
                token,
                self.all_eth_tokens[token]['address'],
                self.all_eth_tokens[token]['decimal'],
                account
            )
            if token_balance == 0:
                continue

            usd_value = token_balance * usd_price
            if append_or_remove == 'append':
                account_balance = self.balances['ETH'][account]
                account_balance[token] = balance
                account_balance['usd_value'] = account_balance['usd_value'] + usd_value

            self.totals[token] = {
                'amount': add_or_sub(self.totals[token].get('amount', 0), token_balance),
                'usd_value': add_or_sub(self.totals.get('usd_value', 0), usd_value)
            }

    def add_blockchain_account(self, blockchain, account):
        return self.modify_blockchain_account(blockchain, account, 'append', operator.add)

    def remove_blockchain_account(self, blockchain, account):
        return self.modify_blockchain_account(blockchain, account, 'remove', operator.sub)

    def modify_blockchain_account(self, blockchain, account, append_or_remove, add_or_sub):

        if blockchain == 'BTC':
            if append_or_remove == 'remove' and account not in self.accounts['BTC']:
                raise InputError('Tried to remove a non existing BTC account')
            self.modify_btc_account(account, append_or_remove, add_or_sub)

        elif blockchain == 'ETH':
            if append_or_remove == 'remove' and account not in self.accounts['ETH']:
                raise InputError('Tried to remove a non existing ETH account')
            self.modify_eth_account(account, append_or_remove, add_or_sub)
        else:
            raise InputError(
                'Unsupported blockchain {} provided at remove_blockchain_account'.format(
                    blockchain)
            )

        return {'per_account': self.balances, 'totals': self.totals}

    def query_ethereum_tokens(self, tokens, eth_balances):
        token_balances = {}
        token_usd_price = {}
        for token in tokens:
            usd_price = self.inquirer.find_usd_price(token)
            if usd_price == 0:
                # skip tokens that have no price
                continue
            token_usd_price[token] = usd_price

            token_balances[token] = self.ethchain.get_multitoken_balance(
                token,
                self.all_eth_tokens[token]['address'],
                self.all_eth_tokens[token]['decimal'],
                self.accounts['ETH'],
            )

        for token, token_accounts in token_balances.items():
            token_total = FVal(0)
            for account, balance in token_accounts.items():
                token_total += balance
                usd_value = balance * token_usd_price[token]
                eth_balances[account][token] = balance
                eth_balances[account]['usd_value'] = eth_balances[account]['usd_value'] + usd_value

            self.totals[token] = {
                'amount': token_total,
                'usd_value': token_total * token_usd_price[token]
            }

        self.balances['ETH'] = eth_balances

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
        self.balances['ETH'] = eth_balances  # but they are not complete until token query

        # And now for tokens
        self.query_ethereum_tokens(self.owned_eth_tokens, eth_balances)
