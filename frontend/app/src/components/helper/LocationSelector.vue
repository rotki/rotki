<template>
  <v-autocomplete
    v-bind="$attrs"
    data-cy="location-input"
    :value="value"
    :disabled="pending"
    :items="locations"
    item-value="identifier"
    item-text="name"
    auto-select-first
    @input="change"
    v-on="$listeners"
  >
    <template #item="{ item, attrs, on }">
      <location-icon
        :id="`balance-location__${item.identifier}`"
        v-bind="attrs"
        horizontal
        :item="item"
        no-padding
        v-on="on"
      />
    </template>
    <template #selection="{ item, attrs, on }">
      <location-icon
        v-bind="attrs"
        horizontal
        :item="item"
        no-padding
        v-on="on"
      />
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { tradeLocations } from '@/components/history/consts';
import LocationIcon from '@/components/history/LocationIcon.vue';

export default defineComponent({
  name: 'LocationSelector',
  components: { LocationIcon },
  props: {
    value: { required: false, type: String, default: '' },
    pending: { required: false, type: Boolean, default: false }
  },
  emits: ['change'],
  setup(_, { emit }) {
    const change = (_value: string) => emit('change', _value);

    return {
      locations: tradeLocations,
      change
    };
  }
});
</script>
