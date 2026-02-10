<script setup lang="ts">
import type { Eth2ValidatorEntry } from '@rotki/common';
import ValidatorDisplay from '@/components/display/ValidatorDisplay.vue';

const model = defineModel<Eth2ValidatorEntry[]>({ required: true });

withDefaults(defineProps<{
  items: Eth2ValidatorEntry[];
  loading?: boolean;
  dense?: boolean;
  hideDetails?: boolean;
  hint?: string;
}>(), {
  loading: false,
  dense: false,
  hideDetails: false,
  hint: undefined,
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    :options="items"
    :loading="loading"
    :disabled="loading"
    :dense="dense"
    :hide-details="hideDetails"
    :hint="hint"
    hide-selected
    hide-no-data
    chips
    clearable
    auto-select-first
    return-object
    key-attr="publicKey"
    text-attr="index"
    :item-height="68"
    variant="outlined"
    :label="t('validator_filter_input.label')"
  >
    <template #item="{ item }">
      <ValidatorDisplay
        :validator="item"
      />
    </template>
    <template #selection="{ item }">
      <ValidatorDisplay
        :validator="item"
        horizontal
      />
    </template>
  </RuiAutoComplete>
</template>
