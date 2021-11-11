<template>
  <span
    class="d-flex align-center"
    :class="{
      'flex-row': horizontal,
      'flex-column': !horizontal,
      'py-4': !noPadding
    }"
  >
    <span>
      <v-img
        v-if="item.imageIcon"
        :width="size"
        contain
        position="left"
        :max-height="size"
        :src="item.icon"
      />
      <component
        :is="item.component"
        v-else-if="typeof item.component !== 'undefined'"
        :width="size"
      />
      <v-icon v-else color="accent"> {{ item.icon }} </v-icon>
    </span>
    <span v-if="!icon" :class="horizontal ? 'ml-3' : null" class="mt-1">
      {{ item.name }}
    </span>
  </span>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { TradeLocationData } from '@/components/history/type';

const LocationIcon = defineComponent({
  name: 'LocationIcon',
  props: {
    item: {
      required: true,
      type: Object as PropType<TradeLocationData>
    },
    horizontal: { required: false, type: Boolean, default: false },
    icon: { required: false, type: Boolean, default: false },
    size: { required: false, type: String, default: '24px' },
    noPadding: { required: false, type: Boolean, default: false }
  }
});
export default LocationIcon;
</script>
