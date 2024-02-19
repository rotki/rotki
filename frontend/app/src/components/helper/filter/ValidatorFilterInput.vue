<script setup lang="ts">
import type { Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    modelValue: Eth2ValidatorEntry[];
    items: Eth2ValidatorEntry[];
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: Eth2ValidatorEntry[]): void;
}>();

const model = useSimpleVModel(props, emit);

const search: Ref<string> = ref('');

function filter(_value: string, queryText: string, item?: { raw: Eth2ValidatorEntry }) {
  const raw = item?.raw;
  if (!raw)
    return false;

  const { publicKey, index } = raw;
  return publicKey.includes(queryText)
    || index.toString().includes(queryText)
    || false;
}

function removeValidator(validator: Eth2ValidatorEntry) {
  const selection = [...props.modelValue];
  const index = selection.findIndex(v => v.publicKey === validator.publicKey);
  if (index >= 0)
    selection.splice(index, 1);

  emit('update:model-value', selection);
}

const { t } = useI18n();
</script>

<template>
  <VAutocomplete
    v-model:search-input="search"
    v-model="model"
    :custom-filter="filter"
    :items="items"
    :loading="loading"
    :disabled="loading"
    hide-details
    hide-selected
    hide-no-data
    return-object
    chips
    clearable
    multiple
    flat
    density="compact"
    variant="outlined"
    item-value="publicKey"
    :label="t('validator_filter_input.label')"
    :open-on-clear="false"
    item-title="publicKey"
  >
    <template #item="{ item }">
      <ValidatorDisplay
        class="py-2"
        :validator="item.raw"
      />
    </template>
    <template #selection="{ item }">
      <RuiChip
        size="sm"
        class="text-truncate m-0.5"
        closeable
        @click:close="removeValidator(item.raw)"
      >
        <ValidatorDisplay
          :validator="item.raw"
          horizontal
        />
      </RuiChip>
    </template>
  </VAutocomplete>
</template>
