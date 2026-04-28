<script setup lang="ts">
import { isValidEthAddress } from '@rotki/common';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';

const modelValue = defineModel<string>({ required: true });

const { location } = defineProps<{
  location: string;
  errorMessages: string[];
}>();

const emit = defineEmits<{
  blur: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { getAddresses } = useAccountAddresses();
const { matchChain } = useSupportedChains();
const { getAddressName } = useAddressNameResolution();

const chain = computed<string | undefined>(() => matchChain(location));

const addressSuggestions = computed<string[]>(() => {
  const matched = get(chain);
  if (!matched)
    return [];
  return getAddresses(matched);
});

function renderAsAccount(value: string | undefined): boolean {
  return !!get(chain) && !!value && isValidEthAddress(value);
}

function filterAddress(item: string, queryText: string): boolean {
  if (!queryText)
    return true;

  const query = queryText.toLowerCase();
  if (item.toLowerCase().includes(query))
    return true;

  const matched = get(chain);
  if (!matched)
    return false;

  const name = getAddressName(item, matched);
  return !!name && name.toLowerCase().includes(query);
}
</script>

<template>
  <RuiAutoComplete
    v-model="modelValue"
    :options="addressSuggestions"
    :filter="filterAddress"
    clearable
    custom-value
    variant="outlined"
    data-cy="location-label"
    :label="t('transactions.events.form.account_address.label')"
    :error-messages="errorMessages"
    auto-select-first
    @blur="emit('blur')"
  >
    <template #item="{ item }">
      <AccountDisplay
        v-if="renderAsAccount(item) && chain"
        class="py-1"
        :account="{ address: item, chain }"
        hide-chain-icon
      />
      <span v-else>{{ item }}</span>
    </template>
    <template #selection="{ item }">
      <AccountDisplay
        v-if="renderAsAccount(item) && chain"
        size="16px"
        :account="{ address: item, chain }"
        hide-chain-icon
      />
      <span v-else>{{ item }}</span>
    </template>
  </RuiAutoComplete>
</template>
