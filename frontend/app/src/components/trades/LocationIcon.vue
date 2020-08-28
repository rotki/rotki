<template>
  <span
    class="d-flex align-center"
    :class="horizontal ? 'flex-row' : 'flex-column'"
  >
    <span>
      <v-img
        v-if="item.identifier !== 'external'"
        width="24px"
        contain
        position="left"
        max-height="24px"
        :src="item.icon"
      />
      <v-icon v-else color="accent">mdi-book-open</v-icon>
    </span>
    <span :class="horizontal ? 'ml-2' : null">
      {{ item.name }}
    </span>
  </span>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { TradeLocationData } from '@/components/trades/type';

@Component({})
export default class LocationIcon extends Vue {
  @Prop({ required: true })
  item!: TradeLocationData;
  @Prop({ required: false, type: Boolean, default: false })
  horizontal!: boolean;
}
</script>
