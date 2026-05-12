<script setup lang="ts">
import { isValidatorAccount } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';
import ValidatorDisplay from '@/modules/shell/components/display/ValidatorDisplay.vue';

type OptionKind = 'address' | 'validator';

interface AccountOption {
  id: string;
  kind: OptionKind;
  validatorIndex?: number;
  searchText: string;
}

const modelValue = defineModel<readonly string[]>({ required: true });

const {
  chain,
  disabled = false,
  label = '',
} = defineProps<{
  chain: string;
  label?: string;
  disabled?: boolean;
}>();

const OptionKind = {
  ADDRESS: 'address',
  VALIDATOR: 'validator',
} as const satisfies Record<string, OptionKind>;

const { t } = useI18n({ useScope: 'global' });

const { accounts } = storeToRefs(useBlockchainAccountsStore());
const { getAddressName } = useAddressNameResolution();

const options = computed<AccountOption[]>(() => {
  const list = get(accounts)[chain] ?? [];
  const seen = new Set<string>();
  const built: AccountOption[] = [];

  for (const account of list) {
    if (isValidatorAccount(account)) {
      const id = account.data.publicKey;
      if (seen.has(id))
        continue;
      seen.add(id);
      const index = account.data.index;
      built.push({
        id,
        kind: OptionKind.VALIDATOR,
        validatorIndex: index,
        searchText: [id, String(index), account.label].filter(Boolean).join(' ').toLowerCase(),
      });
    }
    else if (account.data.type === 'address') {
      const id = account.data.address;
      if (seen.has(id))
        continue;
      seen.add(id);
      const ens = getAddressName(id, chain);
      built.push({
        id,
        kind: OptionKind.ADDRESS,
        searchText: [id, account.label, ens].filter(Boolean).join(' ').toLowerCase(),
      });
    }
  }

  built.sort((a, b) => a.id.localeCompare(b.id));
  return built;
});

function filterOption(option: AccountOption, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q)
    return true;
  return option.searchText.includes(q);
}

defineExpose({
  filterOption,
  options,
});
</script>

<template>
  <RuiAutoComplete
    :model-value="[...modelValue]"
    :options="options"
    :label="label || t('chain_account_multi_select.label')"
    :disabled="disabled"
    :filter="filterOption"
    key-attr="id"
    text-attr="id"
    variant="outlined"
    chips
    dense
    hide-details
    auto-select-first
    @update:model-value="modelValue = $event"
  >
    <template #selection="{ item }">
      <ValidatorDisplay
        v-if="item.kind === OptionKind.VALIDATOR && item.validatorIndex !== undefined"
        horizontal
        :validator="{ publicKey: item.id, index: item.validatorIndex }"
      />
      <AccountDisplay
        v-else
        hide-chain-icon
        :account="{ address: item.id, chain }"
      />
    </template>
    <template #item="{ item }">
      <ValidatorDisplay
        v-if="item.kind === OptionKind.VALIDATOR && item.validatorIndex !== undefined"
        :validator="{ publicKey: item.id, index: item.validatorIndex }"
      />
      <AccountDisplay
        v-else
        hide-chain-icon
        :account="{ address: item.id, chain }"
      />
    </template>
  </RuiAutoComplete>
</template>
