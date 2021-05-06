<template>
  <span
    class="d-flex align-center py-4"
    :class="horizontal ? 'flex-row' : 'flex-column'"
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
      <v-icon v-else color="accent"> {{ item.icon }} </v-icon>
    </span>
    <span v-if="!icon" :class="horizontal ? 'ml-2' : null" class="mt-2">
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
  @Prop({ required: false, type: Boolean, default: false })
  icon!: boolean;
  @Prop({ required: false, type: String, default: '24px' })
  size!: string;
}
</script>
