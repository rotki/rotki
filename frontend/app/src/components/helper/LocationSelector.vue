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
import { get } from '@vueuse/core';
import { computed, defineComponent, PropType, toRefs } from 'vue';
import { tradeLocations } from '@/components/history/consts';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocationData } from '@/components/history/type';

export default defineComponent({
  name: 'LocationSelector',
  components: { LocationIcon },
  props: {
    value: { required: false, type: String, default: '' },
    pending: { required: false, type: Boolean, default: false },
    items: {
      required: false,
      type: Array as PropType<string[]>,
      default: () => []
    },
    excludes: {
      required: false,
      type: Array as PropType<string[]>,
      default: () => []
    }
  },
  emits: ['change'],
  setup(props, { emit }) {
    const { items, excludes } = toRefs(props);

    const change = (_value: string) => emit('change', _value);

    const locations = computed<TradeLocationData[]>(() => {
      const itemsVal = get(items);
      const excludesVal = get(excludes);

      return tradeLocations.filter(item => {
        const included =
          itemsVal && itemsVal.length > 0
            ? itemsVal.includes(item.identifier)
            : true;

        const excluded =
          excludesVal && excludesVal.length > 0
            ? excludesVal.includes(item.identifier)
            : false;

        return included && !excluded;
      });
    });

    return {
      locations,
      change
    };
  }
});
</script>
