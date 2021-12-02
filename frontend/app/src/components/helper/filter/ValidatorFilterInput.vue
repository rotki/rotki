<template>
  <v-card id="validator-filter-input" flat>
    <v-autocomplete
      :class="$style.filter"
      attach="#validator-filter-input"
      :filter="filter"
      :value="selection"
      :items="items"
      :search-input.sync="search"
      :loading="loading"
      :disabled="loading"
      hide-details
      hide-selected
      hide-no-data
      return-object
      chips
      single-line
      clearable
      dense
      outlined
      :label="$t('validator_filter_input.label')"
      :open-on-clear="false"
      item-text="publicKey"
      @input="input($event)"
    >
      <template #item="{ item }">
        <validator-display :validator="item" />
      </template>
      <template #selection="{ item }">
        <validator-display :validator="item" horizontal />
      </template>
    </v-autocomplete>
  </v-card>
</template>

<script lang="ts">
import { Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import ValidatorDisplay from '@/components/helper/display/icons/ValidatorDisplay.vue';

export default defineComponent({
  name: 'ValidatorFilterInput',
  components: { ValidatorDisplay },
  props: {
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
  },
  emits: ['input'],
  setup(props, { emit }) {
    const search = ref('');
    const { value } = toRefs(props);
    const input = (value: Eth2ValidatorEntry | null) => {
      emit('input', !value ? [] : [value.publicKey]);
    };
    const selection = computed(() => {
      const currentFilter = value.value;
      return currentFilter.length === 0 ? '' : currentFilter[0];
    });

    const filter = (
      { publicKey, validatorIndex }: Eth2ValidatorEntry,
      queryText: string
    ) => {
      return (
        publicKey.indexOf(queryText) >= 0 ||
        validatorIndex.toString().indexOf(queryText) >= 0
      );
    };
    return {
      input,
      filter,
      selection,
      search
    };
  }
});
</script>

<style module lang="scss">
.filter {
  border-radius: 4px !important;
}
</style>
