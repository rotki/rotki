import type { Ref, WritableComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { Blockchain } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { listParam, type PillParams, stringParam, toPillParams } from '@/modules/core/table/param-refs';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { getModuleEnabled, Module } from '@/modules/session/use-module-enabled';

/** The keys the blockchain balances table filters on. Not wire keys: both narrow it in memory. */
const BlockchainBalanceFilterKeys = {
  CHAINS: 'chains',
  SEARCH: 'search',
} as const;

/**
 * The pill-bar fields for the blockchain balances table: which chains to total, and a keyword over
 * the asset.
 *
 * Both were controls beside the table — a chain multi-select and a search box. Param-bound, because
 * the page holds the aggregated balances already: the chains narrow what is summed, and the keyword
 * is matched against each row's asset name and symbol.
 */
export function useBlockchainBalanceFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const resolvers = useSharedFieldResolvers();
  const { supportedChains } = useSupportedChains();

  // The same list the chain select offered: every supported chain, minus eth2 while the module is
  // off, because its balances are not in this table then either.
  const chains = (): string[] => {
    const ids = get(supportedChains).map(chain => chain.id);
    return getModuleEnabled(Module.ETH2) ? ids : ids.filter(id => id !== Blockchain.ETH2);
  };

  return [
    decorateSharedField(
      toParamFieldDef({
        key: 'chain',
        label: (): string => t('common.chain'),
        // The select was multi-valued and so is the pill: the table totals the chains it is given.
        multiple: true,
        paramKey: BlockchainBalanceFilterKeys.CHAINS,
        suggest: chains,
        to: 'both',
      }),
      SharedFieldKinds.CHAIN,
      resolvers,
    ),
    toParamFieldDef({
      freeText: true,
      hint: (): string => t('blockchain_balances.filter.search_hint'),
      key: 'search',
      label: (): string => t('common.actions.search'),
      multiple: false,
      paramKey: BlockchainBalanceFilterKeys.SEARCH,
      to: 'both',
    }),
  ];
}

/** The page's two refs as the bar's params bag. */
export function blockchainBalanceParams(
  chains: Ref<string[]>,
  search: Ref<string>,
): WritableComputedRef<PillParams> {
  return toPillParams({
    chains: listParam(chains),
    search: stringParam(search),
  });
}
