<script setup lang="ts">
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';

const locationLabel = defineModel<string>('locationLabel', { required: true });
const address = defineModel<string>('address', { required: true });

const props = defineProps<{
  location: string;
  errorMessages: {
    address: string[];
    locationLabel: string[];
  };
}>();

const emit = defineEmits<{
  blur: [source: 'address' | 'locationLabel'];
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
  <div class="grid md:grid-cols-2 gap-4">
    <AutoCompleteWithSearchSync
      v-model="locationLabel"
      :items="addressSuggestions"
      clearable
      data-cy="location-label"
      :label="t('transactions.events.form.account_address.label')"
      :error-messages="errorMessages.locationLabel"
      auto-select-first
      @blur="emit('blur', 'locationLabel')"
    />

    <RuiTextField
      v-model="address"
      clearable
      variant="outlined"
      data-cy="address"
      :label="t('transactions.events.form.contract_address.label')"
      :error-messages="errorMessages.address"
      @blur="emit('blur', 'address')"
    />
  </div>
</template>
