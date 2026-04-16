<script setup lang="ts">
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';

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

const addressSuggestions = computed(() => {
  const chain = matchChain(location);
  if (!chain)
    return [];
  return getAddresses(chain);
});
</script>

<template>
  <AutoCompleteWithSearchSync
    v-model="modelValue"
    :items="addressSuggestions"
    clearable
    data-cy="location-label"
    :label="t('transactions.events.form.account_address.label')"
    :error-messages="errorMessages"
    auto-select-first
    @blur="emit('blur')"
  />
</template>
