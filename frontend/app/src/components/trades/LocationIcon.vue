<template>
  <span class="d-flex flex-row align-center">
    <span>
      <v-img
        v-if="item.identifier !== 'external'"
        width="34px"
        contain
        position="left"
        max-height="24px"
        :src="item.icon"
      />
      <v-icon v-else color="accent" class="mr-2">mdi-book-open</v-icon>
    </span>
    <span>
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
}
</script>
