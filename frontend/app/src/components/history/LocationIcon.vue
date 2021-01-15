<template>
  <span
    class="d-flex align-center pt-2 pb-2"
    :class="horizontal ? 'flex-row' : 'flex-column'"
  >
    <span>
      <v-img
        v-if="item.imageIcon"
        width="24px"
        contain
        position="left"
        max-height="24px"
        :src="item.icon"
      />
      <v-icon v-else color="accent"> {{ item.icon }} </v-icon>
    </span>
    <span :class="horizontal ? 'ml-2' : null" class="mt-2">
      {{ item.name }}
    </span>
  </span>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { TradeLocationData } from '@/components/history/type';

@Component({})
export default class LocationIcon extends Vue {
  @Prop({ required: true })
  item!: TradeLocationData;
  @Prop({ required: false, type: Boolean, default: false })
  horizontal!: boolean;
}
</script>
