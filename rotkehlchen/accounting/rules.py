from typing import TYPE_CHECKING, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry, get_event_type_identifier
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.db.constants import NO_ACCOUNTING_COUNTERPARTY

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
    from rotkehlchen.db.dbhandler import DBHandler


def make_default_accounting_settings(pot: 'AccountingPot') -> dict[int, BaseEventSettings]:
    """
    Returns accounting settings for events that can come from various decoders and thus don't have
    any particular protocol. These settings also allow users to customize events in the UI.
    TODO: Remove this hardcoded rules and add them to the database along the evm modules rules.
    """
    result = {}
    result[get_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.FEE, CPT_GAS)] = BaseEventSettings(  # noqa: E501
        taxable=pot.settings.include_gas_costs,
        count_entire_amount_spend=pot.settings.include_gas_costs,
        count_cost_basis_pnl=pot.settings.include_crypto2crypto,
        method='spend',
    )
    result[get_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.NONE)] = BaseEventSettings(  # noqa: E501
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='spend',
    )
    result[get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.NONE)] = BaseEventSettings(  # noqa: E501
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='acquisition',
    )
    result[get_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.FEE)] = BaseEventSettings(  # noqa: E501
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='spend',
    )
    result[get_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.NONE)] = BaseEventSettings(  # noqa: E501
        taxable=False,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='spend',
    )
    result[get_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.NONE)] = BaseEventSettings(  # noqa: E501
        taxable=False,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='spend',
    )
    result[get_event_type_identifier(HistoryEventType.RENEW, HistoryEventSubType.NONE)] = BaseEventSettings(  # noqa: E501
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='spend',
    )
    result[get_event_type_identifier(HistoryEventType.TRADE, HistoryEventSubType.SPEND)] = BaseEventSettings(  # noqa: E501
        taxable=True,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=True,
        method='spend',
        accounting_treatment=TxAccountingTreatment.SWAP,
    )
    result[get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.AIRDROP)] = BaseEventSettings(  # noqa: E501
        taxable=False,
        # count_entire_amount_spend and count_cost_basis_pnl don't matter for acquisitions.
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='acquisition',
    )
    result[get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.REWARD)] = BaseEventSettings(  # noqa: E501
        taxable=True,
        # count_entire_amount_spend and count_cost_basis_pnl don't matter for acquisitions.
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='acquisition',
    )
    result[get_event_type_identifier(HistoryEventType.STAKING, HistoryEventSubType.REWARD)] = BaseEventSettings(  # noqa: E501
        taxable=True,
        # count_entire_amount_spend and count_cost_basis_pnl don't matter for acquisitions.
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='acquisition',
    )
    result[get_event_type_identifier(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)] = BaseEventSettings(  # noqa: E501
        taxable=False,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='spend',
    )
    result[get_event_type_identifier(HistoryEventType.STAKING, HistoryEventSubType.REMOVE_ASSET)] = BaseEventSettings(  # noqa: E501
        taxable=False,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='acquisition',
    )
    return result


class AccountingRulesManager:
    """Handle the query of accounting rules for history events"""

    def __init__(
            self,
            database: 'DBHandler',
            evm_aggregators: 'EVMAccountingAggregators',
            pot: 'AccountingPot',
    ):
        self.database = database
        self.aggregators = evm_aggregators
        self.pot = pot
        self.event_settings: dict[int, BaseEventSettings] = {}

    def _query_db_rules(self) -> None:
        """Query the accounting rules in the db and update event_settings with them"""
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT type, subtype, counterparty, taxable, count_entire_amount_spend, '
                'count_cost_basis_pnl, method, accounting_treatment FROM accounting_rules',
            )
            for entry in cursor:
                rule = BaseEventSettings.deserialize_from_db(entry[3:])
                key = get_event_type_identifier(
                    event_type=HistoryEventType.deserialize(entry[0]),
                    event_subtype=HistoryEventSubType.deserialize(entry[1]),
                    counterparty=entry[2] if entry[2] != NO_ACCOUNTING_COUNTERPARTY else None,
                )
                self.event_settings[key] = rule

    def get_event_settings(self, event: HistoryBaseEntry) -> Optional[BaseEventSettings]:
        """Return a matching rule for the event if it exists"""
        rule = self.event_settings.get(event.get_type_identifier(), None)
        if isinstance(event, EvmEvent) is False or rule is not None:
            return rule

        return self.event_settings.get(event.get_type_identifier(include_counterparty=False), None)

    def reset(self) -> None:
        self.aggregators.reset()
        self.event_settings = (  # Using | operator is fine since keys are unique
            self.aggregators.get_accounting_settings(self.pot) |
            make_default_accounting_settings(self.pot)
        )
        self._query_db_rules()

    def clean_rules(self) -> None:
        """
        Remove the rules from memory. Should be done after finishing with the accounting process
        to avoid having many dynamic objects in memory since the rules come from the database
        """
        self.event_settings.clear()
