import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * The chain pill: which chains of the shown category an account has to be on. Param-bound like the
 * account and tag pills, so this table declares no matchers at all — every filter it has reaches
 * the request the same way.
 *
 * The values are the category's own chain ids (evm has around fifteen, bitcoin two, solana one),
 * and a group that survives is narrowed to the chains that matched, which is what makes its value
 * add up to the chains being shown rather than all of them.
 */
export function toAccountChainField(
  t: Translate,
  resolvers: SharedFieldResolvers,
  chains: () => string[],
): FieldDef {
  return decorateSharedField(
    toParamFieldDef({
      key: 'chain',
      label: (): string => t('account_balances.filter_field_labels.chain'),
      multiple: true,
      paramKey: 'chain',
      suggest: chains,
      to: 'both',
    }),
    SharedFieldKinds.CHAIN,
    resolvers,
  );
}
