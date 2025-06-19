<script setup lang="ts">
import LocationSelector from '@/components/helper/LocationSelector.vue';

const timestamp = defineModel<number>('timestamp', { required: true });
const location = defineModel<string>('location', { required: true });

withDefaults(defineProps<{
  locationDisabled?: boolean;
  dateDisabled?: boolean;
  errorMessages: {
    timestamp: string[];
    location: string[];
  };
}>(), {
  dateDisabled: false,
  locationDisabled: false,
});

const emit = defineEmits<{
  blur: [source: 'location' | 'timestamp'];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="grid md:grid-cols-2 gap-4 mb-4">
    <RuiDateTimePicker
      v-model="timestamp"
      :label="t('common.datetime')"
      persistent-hint
      max-date="now"
      color="primary"
      variant="outlined"
      accuracy="millisecond"
      :disabled="dateDisabled"
      data-cy="datetime"
      :hint="t('transactions.events.form.datetime.hint')"
      :error-messages="errorMessages.timestamp"
      @blur="emit('blur', 'timestamp')"
    />
    <LocationSelector
      v-model="location"
      :disabled="locationDisabled"
      data-cy="location"
      :label="t('common.location')"
      :error-messages="errorMessages.location"
      @blur="emit('blur', 'location')"
    />
    <slot />
  </div>
</template>
