<script setup lang="ts">
import type { Eth2ValidatorEntry } from '@rotki/common';
import ValidatorDisplay from '@/components/display/ValidatorDisplay.vue';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<Eth2ValidatorEntry[]>({ required: true });

withDefaults(defineProps<{
  items: Eth2ValidatorEntry[];
  loading?: boolean;
}>(), {
  loading: false,
});

const { t } = useI18n();
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    :options="items"
    :loading="loading"
    :disabled="loading"
    hide-details
    hide-selected
    hide-no-data
    chips
    clearable
    dense
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
        class="py-2"
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
