<script setup lang="ts">
import EventLocationLabel from '@/modules/history/management/forms/common/EventLocationLabel.vue';

const locationLabel = defineModel<string>('locationLabel', { required: true });
const address = defineModel<string>('address', { required: true });

defineProps<{
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
</script>

<template>
  <div class="grid md:grid-cols-2 gap-4">
    <EventLocationLabel
      v-model="locationLabel"
      :location="location"
      :error-messages="errorMessages.locationLabel"
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
