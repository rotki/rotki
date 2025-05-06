<script setup lang="ts">
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';

const modelValue = defineModel<string>({ required: true });

const props = defineProps<{
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
  const chain = matchChain(props.location);
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
