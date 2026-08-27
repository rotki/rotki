import type { MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toAccountChainField } from '@/modules/accounts/blockchain-account-fields';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountOptions } from '@/modules/accounts/use-blockchain-account-options';
import { toAccountField } from '@/modules/core/table/filters/shared/account-field';
import { type TagFieldOption, toTagsField } from '@/modules/core/table/filters/shared/tag-field';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useTagFieldOptions } from '@/modules/core/table/filters/shared/use-tag-field-options';

/**
 * The pill-bar `FieldDef`s for the blockchain accounts table: account, chain and tags, all three
 * param-bound. The table declares no matchers, so every filter it has reaches the request the same
 * way and there is one mechanism to reason about instead of two.
 */
export function useBlockchainAccountFields(category: MaybeRefOrGetter<string>): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });

  const { chainIds } = useAccountCategoryHelper(category);
  const shared = useSharedFieldResolvers();
  const accountOptions = useBlockchainAccountOptions(category);

  const tagOptions = useTagFieldOptions();

  return [
    toAccountField(
      {
        label: (): string => t('account_balances.filter_field_labels.account'),
        paramKey: 'addresses',
        to: 'both',
      },
      accountOptions,
    ),
    toAccountChainField(t, shared, (): string[] => get(chainIds)),
    toTagsField(t, (): TagFieldOption[] => get(tagOptions)),
  ];
}
