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
      <v-icon v-else color="accent"> {{ item.icon }} </v-icon>
    </span>
    <span v-if="!icon" :class="horizontal ? 'ml-3' : null" class="mt-1">
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
  @Prop({ required: false, type: Boolean, default: false })
  noPadding!: boolean;
}
</script>
