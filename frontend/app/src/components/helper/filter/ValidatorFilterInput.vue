<template>
  <v-card flat>
    <v-autocomplete
      :class="$style.filter"
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
          :class="$style.chip"
          close
          @click:close="removeValidator(item.publicKey)"
        >
          <validator-display :validator="item" horizontal />
        </v-chip>
      </template>
    </v-autocomplete>
  </v-card>
</template>

<script setup lang="ts">
import { Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';
import { PropType } from 'vue';
import ValidatorDisplay from '@/components/helper/display/icons/ValidatorDisplay.vue';
import { useTheme } from '@/composables/common';

const props = defineProps({
  value: {
    required: true,
    type: Array as PropType<string[]>
  },
  items: {
    required: true,
    type: Array as PropType<Eth2ValidatorEntry[]>
  },
  loading: {
    required: false,
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['input']);

const search = ref('');
const { value } = toRefs(props);
const input = (value: (Eth2ValidatorEntry | string)[]) => {
  const selection = value.map(v => (typeof v === 'string' ? v : v.publicKey));
  emit('input', selection);
};

const filter = (
  { publicKey, validatorIndex }: Eth2ValidatorEntry,
  queryText: string
) => {
  return (
    publicKey.indexOf(queryText) >= 0 ||
    validatorIndex.toString().indexOf(queryText) >= 0
  );
};

const removeValidator = (publicKey: string) => {
  const selection = [...get(value)];
  const index = selection.indexOf(publicKey);
  if (index >= 0) {
    selection.splice(index, 1);
  }
  input(selection);
};

const { dark } = useTheme();

const { t } = useI18n();
</script>

<style module lang="scss">
.filter {
  border-radius: 4px !important;
}

.chip {
  margin: 2px;
}
</style>
