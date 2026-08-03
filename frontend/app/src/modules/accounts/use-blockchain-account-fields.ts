import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountOptions } from '@/modules/accounts/use-blockchain-account-options';
import { type TagFieldOption, toAccountChainField, toAccountTagsField } from '@/modules/core/table/filters/blockchain-account-fields';
import { toAccountField } from '@/modules/core/table/filters/shared/account-field';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

/**
 * The pill-bar `FieldDef`s for the blockchain accounts table: account, chain and tags, all three
 * param-bound. The table declares no matchers, so every filter it has reaches the request the same
 * way and there is one mechanism to reason about instead of two.
 *
 * All three are built inside computeds so their labels track the locale: a field built once at
 * setup keeps the language it was created in until the component remounts.
 */
export function useBlockchainAccountFields(category: MaybeRefOrGetter<string>): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });

  const { tags } = storeToRefs(useSessionMetadataStore());

  const { chainIds } = useAccountCategoryHelper(category);
  // Address and chain-name resolution is the same for every table filtering on them, so it comes
  // from one place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const accountOptions = useBlockchainAccountOptions(category);

  const tagOptions = computed<TagFieldOption[]>(() => get(tags).map(tag => ({
    name: tag.name,
    swatch: { background: `#${tag.backgroundColor}`, foreground: `#${tag.foregroundColor}` },
  })));

  // The account pill is history's, bound to this table's own `addresses` param and its own,
  // category-scoped account list.
  const accountField = computed<FieldDef>(() => toAccountField(
    { label: t('account_balances.filter_field_labels.account'), paramKey: 'addresses', to: 'both' },
    accountOptions,
  ));
  const chainField = computed<FieldDef>(() => toAccountChainField(t, shared, (): string[] => get(chainIds)));
  const tagsField = computed<FieldDef>(() => toAccountTagsField(t, (): TagFieldOption[] => get(tagOptions)));

  return computed<FieldDef[]>(() => [get(accountField), get(chainField), get(tagsField)]);
}
