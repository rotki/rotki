interface UseEventActionDescriptionsReturn {
  readonly describe: (verbKey: string) => string | undefined;
}

/**
 * Plain-language one-liners for each picker verb, keyed by the serialized
 * `EventCategory` (the space-joined lowercase enum name that the backend emits
 * as the row's `verbKey`, e.g. `swap out`). The i18n catalogue uses snake_case
 * keys, so this map bridges the spaced verb key to a literal `t()` call; the
 * project lint rule forbids dynamic translation keys, hence the explicit list.
 *
 * A verb with no entry falls back to the derived `type · subtype` subtitle, so
 * new backend verbs degrade gracefully instead of showing a missing key.
 */
export function useEventActionDescriptions(): UseEventActionDescriptionsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const descriptions = computed<Record<string, string>>(() => ({
    'account deposit': t('history_event_action.picker.description.account_deposit'),
    'account withdrawal': t('history_event_action.picker.description.account_withdrawal'),
    'airdrop': t('history_event_action.picker.description.airdrop'),
    'apply': t('history_event_action.picker.description.apply'),
    'approval': t('history_event_action.picker.description.approval'),
    'attest': t('history_event_action.picker.description.attest'),
    'borrow': t('history_event_action.picker.description.borrow'),
    'bridge deposit': t('history_event_action.picker.description.bridge_deposit'),
    'bridge withdrawal': t('history_event_action.picker.description.bridge_withdrawal'),
    'burn': t('history_event_action.picker.description.burn'),
    'cancel order': t('history_event_action.picker.description.cancel_order'),
    'cashback': t('history_event_action.picker.description.cashback'),
    'cex deposit': t('history_event_action.picker.description.cex_deposit'),
    'cex withdrawal': t('history_event_action.picker.description.cex_withdrawal'),
    'claim reward': t('history_event_action.picker.description.claim_reward'),
    'clawback': t('history_event_action.picker.description.clawback'),
    'combine': t('history_event_action.picker.description.combine'),
    'create block': t('history_event_action.picker.description.create_block'),
    'create project': t('history_event_action.picker.description.create_project'),
    'delegate': t('history_event_action.picker.description.delegate'),
    'deploy': t('history_event_action.picker.description.deploy'),
    'deploy with spend': t('history_event_action.picker.description.deploy_with_spend'),
    'deposit': t('history_event_action.picker.description.deposit'),
    'donate': t('history_event_action.picker.description.donate'),
    'fail': t('history_event_action.picker.description.fail'),
    'fee': t('history_event_action.picker.description.fee'),
    'governance': t('history_event_action.picker.description.governance'),
    'hack loss': t('history_event_action.picker.description.hack_loss'),
    'informational': t('history_event_action.picker.description.informational'),
    'interest': t('history_event_action.picker.description.interest'),
    'liquidation loss': t('history_event_action.picker.description.liquidation_loss'),
    'liquidation reward': t('history_event_action.picker.description.liquidation_reward'),
    'liquidity provision loss': t('history_event_action.picker.description.liquidity_provision_loss'),
    'loss': t('history_event_action.picker.description.loss'),
    'message': t('history_event_action.picker.description.message'),
    'migrate in': t('history_event_action.picker.description.migrate_in'),
    'migrate out': t('history_event_action.picker.description.migrate_out'),
    'mev reward': t('history_event_action.picker.description.mev_reward'),
    'mint nft': t('history_event_action.picker.description.mint_nft'),
    'pay': t('history_event_action.picker.description.pay'),
    'place order': t('history_event_action.picker.description.place_order'),
    'profit': t('history_event_action.picker.description.profit'),
    'protocol deposit': t('history_event_action.picker.description.protocol_deposit'),
    'protocol withdrawal': t('history_event_action.picker.description.protocol_withdrawal'),
    'receive': t('history_event_action.picker.description.receive'),
    'receive donation': t('history_event_action.picker.description.receive_donation'),
    'receive grant': t('history_event_action.picker.description.receive_grant'),
    'receive payment': t('history_event_action.picker.description.receive_payment'),
    'refund': t('history_event_action.picker.description.refund'),
    'renew': t('history_event_action.picker.description.renew'),
    'repay': t('history_event_action.picker.description.repay'),
    'return': t('history_event_action.picker.description.return'),
    'self transaction': t('history_event_action.picker.description.self_transaction'),
    'send': t('history_event_action.picker.description.send'),
    'spam': t('history_event_action.picker.description.spam'),
    'stake deposit': t('history_event_action.picker.description.stake_deposit'),
    'stake exit': t('history_event_action.picker.description.stake_exit'),
    'staking reward': t('history_event_action.picker.description.staking_reward'),
    'swap in': t('history_event_action.picker.description.swap_in'),
    'swap out': t('history_event_action.picker.description.swap_out'),
    'transfer': t('history_event_action.picker.description.transfer'),
    'unstake': t('history_event_action.picker.description.unstake'),
    'update': t('history_event_action.picker.description.update'),
    'withdraw': t('history_event_action.picker.description.withdraw'),
  }));

  function describe(verbKey: string): string | undefined {
    return get(descriptions)[verbKey];
  }

  return { describe };
}
