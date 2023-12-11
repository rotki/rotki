<script setup lang="ts">
import { type Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';

const props = withDefaults(
  defineProps<{
    value: Eth2ValidatorEntry[];
    items: Eth2ValidatorEntry[];
    loading?: boolean;
  }>(),
  {
    loading: false
  }
);

const emit = defineEmits<{
  (e: 'input', value: Eth2ValidatorEntry[]): void;
}>();

const { value } = toRefs(props);

const search: Ref<string> = ref('');

const input = (value: Eth2ValidatorEntry[]) => {
  emit('input', value);
};

const filter = (
  { publicKey, validatorIndex }: Eth2ValidatorEntry,
  queryText: string
) =>
  publicKey.includes(queryText) ||
  validatorIndex.toString().includes(queryText);

const removeValidator = (validator: Eth2ValidatorEntry) => {
  const selection = [...get(value)];
  const index = selection.findIndex(v => v.publicKey === validator.publicKey);
  if (index >= 0) {
    selection.splice(index, 1);
  }
  input(selection);
};

const { t } = useI18n();
</script>

<template>
  <VAutocomplete
    :filter="filter"
    :value="value"
    :items="items"
    :search-input.sync="search"
    :loading="loading"
    :disabled="loading"
    hide-details
    hide-selected
    hide-no-data
    return-object
    chips
    clearable
    multiple
    solo
    flat
    dense
    outlined
    item-value="publicKey"
    :label="t('validator_filter_input.label')"
    :open-on-clear="false"
    item-text="publicKey"
    @input="input($event)"
  >
    <template #item="{ item }">
      <ValidatorDisplay class="py-2" :validator="item" />
    </template>
    <template #selection="{ item }">
      <RuiChip
        size="sm"
        class="text-truncate m-0.5"
        closeable
        @click:close="removeValidator(item)"
      >
        <ValidatorDisplay :validator="item" horizontal />
      </RuiChip>
    </template>
  </VAutocomplete>
</template>
