<template>
  <span
    class="d-flex align-center"
    :class="{
      'flex-row': horizontal,
      'flex-column': !horizontal,
      'py-4': !noPadding
    }"
  >
    <adaptive-wrapper component="span">
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
      <v-icon v-else color="accent" :style="iconStyle">
        {{ item.icon }}
      </v-icon>
    </adaptive-wrapper>
    <span v-if="!icon" :class="horizontal ? 'ml-3' : null" class="mt-1">
      {{ item.name }}
    </span>
  </span>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { TradeLocationData } from '@/components/history/type';

export default defineComponent({
  name: 'LocationIcon',
  components: { AdaptiveWrapper },
  props: {
    item: {
      required: true,
      type: Object as PropType<TradeLocationData>
    },
    horizontal: { required: false, type: Boolean, default: false },
    icon: { required: false, type: Boolean, default: false },
    size: { required: false, type: String, default: '24px' },
    noPadding: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { size } = toRefs(props);
    const iconStyle = computed(() => {
      return {
        fontSize: get(size)
      };
    });

    return {
      iconStyle
    };
  }
});
</script>
