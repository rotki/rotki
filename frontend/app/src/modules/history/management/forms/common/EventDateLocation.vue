<script setup lang="ts">
import LocationSelector from '@/components/helper/LocationSelector.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';

const datetime = defineModel<string>('datetime', { required: true });
const location = defineModel<string>('location', { required: true });

withDefaults(defineProps<{
  locationDisabled?: boolean;
  dateDisabled?: boolean;
  errorMessages: {
    datetime: string[];
    location: string[];
  };
}>(), {
  dateDisabled: false,
  locationDisabled: false,
});

const emit = defineEmits<{
  blur: [source: 'location' | 'datetime'];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="grid md:grid-cols-2 gap-4 mb-4">
    <DateTimePicker
      v-model="datetime"
      :label="t('common.datetime')"
      persistent-hint
      limit-now
      milliseconds
      :disabled="dateDisabled"
      data-cy="datetime"
      :hint="t('transactions.events.form.datetime.hint')"
      :error-messages="errorMessages.datetime"
      @blur="emit('blur', 'datetime')"
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
