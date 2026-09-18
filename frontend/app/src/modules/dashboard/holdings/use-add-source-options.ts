import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import type { RouteLocationAsRelative, RouteLocationRaw } from 'vue-router';
import type { RouteName } from '@/types/router';

export interface AddSourceOption {
  /** Rendered into `data-testid`, so the values are kebab-case like every other test id. */
  readonly key: string;
  readonly icon: RuiIcons;
  readonly label: string;
  /** The page of this kind of source, with the query that opens its add dialog. */
  readonly to: RouteLocationRaw;
}

/** Checks the params against this one route, which the union of every route would not. */
function route<Name extends RouteName>(to: RouteLocationAsRelative<Name>): RouteLocationRaw {
  return withAddDialog(to);
}

/** The page opens its add dialog when it lands with `?add=true`. */
function withAddDialog(to: RouteLocationAsRelative): RouteLocationRaw {
  return { ...to, query: { add: 'true' } };
}

/** Every kind of source a portfolio fills from, each leading to the dialog that adds one. */
export function useAddSourceOptions(): ComputedRef<AddSourceOption[]> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<AddSourceOption[]>(() => [
    { icon: 'lu-evm-accounts', key: 'evm', label: t('dashboard.blockchain_balances.categories.evm'), to: route({ name: '/accounts/evm/[[tab]]', params: { tab: 'accounts' } }) },
    { icon: 'lu-bitcoin-accounts', key: 'bitcoin', label: t('dashboard.blockchain_balances.categories.bitcoin'), to: route({ name: '/accounts/bitcoin/' }) },
    { icon: 'lu-blockchain', key: 'solana', label: t('dashboard.blockchain_balances.categories.solana'), to: route({ name: '/accounts/solana/' }) },
    { icon: 'lu-substrate-accounts', key: 'substrate', label: t('dashboard.blockchain_balances.categories.substrate'), to: route({ name: '/accounts/substrate/' }) },
    { icon: 'lu-building-2', key: 'exchange', label: t('dashboard.holdings.add.exchange'), to: route({ name: '/api-keys/exchanges/' }) },
    { icon: 'lu-landmark', key: 'bank', label: t('dashboard.holdings.add.bank'), to: route({ name: '/api-keys/banks/' }) },
    { icon: 'lu-pencil', key: 'manual', label: t('dashboard.holdings.add.manual'), to: route({ name: '/balances/manual/[[tab]]', params: { tab: 'assets' } }) },
  ]);
}
