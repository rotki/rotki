<script setup lang="ts">
import AutoCompleteWithSearchSync from '@/components/inputs/AutoCompleteWithSearchSync.vue';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { Blockchain } from '@rotki/common';

const locationLabel = defineModel<string>('locationLabel', { required: true });
const address = defineModel<string>('address', { required: true });

defineProps<{
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

const addressSuggestions = computed(() => getAddresses(Blockchain.ETH));
</script>

<template>
  <div class="grid md:grid-cols-2 gap-4">
    <AutoCompleteWithSearchSync
      v-model="locationLabel"
      :items="addressSuggestions"
      clearable
      data-cy="location-label"
      :label="t('transactions.events.form.location_label.label')"
      :error-messages="errorMessages.locationLabel"
      auto-select-first
      @blur="emit('blur', 'locationLabel')"
    />

    <AutoCompleteWithSearchSync
      v-model="address"
      :items="addressSuggestions"
      clearable
      data-cy="address"
      :label="t('transactions.events.form.address.label')"
      :error-messages="errorMessages.address"
      auto-select-first
      @blur="emit('blur', 'address')"
    />
  </div>
</template>
