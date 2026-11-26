<script setup lang="ts">
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';

const modelValue = defineModel<string>({ required: true });

const { location, errorMessages } = defineProps<{
  /** Only suggests the names of exchanges connected on this location; without it, every connected exchange. */
  location?: string;
  errorMessages: string[];
}>();

const emit = defineEmits<{
  blur: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

const suggestions = computed<string[]>(() => {
  const names: string[] = [];
  for (const { location: exchangeLocation, name } of get(connectedExchanges)) {
    if (!name || (location !== undefined && exchangeLocation !== location))
      continue;
    names.push(name);
  }
  return names;
});
</script>

<template>
  <AutoCompleteWithSearchSync
    v-model="modelValue"
    :items="suggestions"
    clearable
    data-testid="location-label"
    :label="t('transactions.events.form.location_label.label')"
    :error-messages="errorMessages"
    auto-select-first
    @blur="emit('blur')"
  />
</template>
