<script setup lang="ts">
import type { Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';

const props = withDefaults(
  defineProps<{
    value: Eth2ValidatorEntry[];
    items: Eth2ValidatorEntry[];
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'input', value: Eth2ValidatorEntry[]): void;
}>();

const { value } = toRefs(props);

function input(value: Eth2ValidatorEntry[]) {
  emit('input', value);
}

const { t } = useI18n();
</script>

<template>
  <RuiAutoComplete
    :value="value"
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
    @input="input($event)"
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
