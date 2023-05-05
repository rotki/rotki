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

const { dark } = useTheme();

const { t } = useI18n();
const css = useCssModule();
</script>

<template>
  <v-card flat>
    <v-autocomplete
      :class="css.filter"
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
      dense
      outlined
      item-value="publicKey"
      :label="t('validator_filter_input.label')"
      :open-on-clear="false"
      item-text="publicKey"
      @input="input($event)"
    >
      <template #item="{ item }">
        <validator-display :validator="item" />
      </template>
      <template #selection="{ item }">
        <v-chip
          small
          :color="dark ? null : 'grey lighten-3'"
          filter
          class="text-truncate"
          :class="css.chip"
          close
          @click:close="removeValidator(item)"
        >
          <validator-display :validator="item" horizontal />
        </v-chip>
      </template>
    </v-autocomplete>
  </v-card>
</template>

<style module lang="scss">
.filter {
  border-radius: 4px !important;
}

.chip {
  margin: 2px;
}
</style>
