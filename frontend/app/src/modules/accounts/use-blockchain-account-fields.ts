import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Matcher } from '@/modules/core/table/filters/use-blockchain-account-filter';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useBlockchainAccountOptions } from '@/modules/accounts/use-blockchain-account-options';
import { type TagFieldOption, toAccountTagsField, toBlockchainAccountFields } from '@/modules/core/table/filters/blockchain-account-fields';
import { toAccountField } from '@/modules/core/table/filters/shared/account-field';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

/**
 * Assembles the pill-bar `FieldDef`s for the blockchain accounts table: the chain matcher plus the
 * account and tag pills, which are param-bound rather than matchers. Both used to be selectors of
 * their own beside the bar; as fields they are two more pills in it.
 */
export function useBlockchainAccountFields(
  matchers: MaybeRefOrGetter<Matcher[]>,
  category: MaybeRefOrGetter<string>,
): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });

  const { tags } = storeToRefs(useSessionMetadataStore());

  // Address and date resolution is the same for every table filtering on them, so it comes from
  // one place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const accountOptions = useBlockchainAccountOptions(category);

  const tagOptions = computed<TagFieldOption[]>(() => get(tags).map(tag => ({
    name: tag.name,
    swatch: { background: `#${tag.backgroundColor}`, foreground: `#${tag.foregroundColor}` },
  })));

  // Both are rebuilt inside a computed like the matcher fields, so their labels track the locale:
  // a field built once at setup keeps the language it was created in until the component remounts.
  //
  // The account pill is history's, bound to this table's own `addresses` param and its own,
  // category-scoped account list.
  const accountField = computed<FieldDef>(() => toAccountField(
    { label: t('account_balances.filter_field_labels.account'), paramKey: 'addresses', to: 'both' },
    accountOptions,
  ));
  const tagsField = computed<FieldDef>(() => toAccountTagsField(t, (): TagFieldOption[] => get(tagOptions)));

  return computed<FieldDef[]>(() => [
    get(accountField),
    ...toBlockchainAccountFields(toValue(matchers), { ...shared, t }),
    get(tagsField),
  ]);
}
