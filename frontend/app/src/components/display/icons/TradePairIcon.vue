<template>
  <div class="trade-pair-icon d-flex flex-row pa-1">
    <crypto-icon :symbol="assets[0]" size="32px" />
    <crypto-icon :symbol="assets[1]" size="32px" />
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class UniswapPoolAsset extends Vue {
  @Prop({
    required: true,
    type: String,
    validator: (value: any) =>
      typeof value === 'string' && value.indexOf('_') > 0
  })
  pair!: string;

  get assets(): string[] {
    return this.pair.split('_');
  }
}
</script>

<style scoped lang="scss">
.trade-pair-icon {
  border-radius: 50%;

  > * {
    width: 32px;
    height: 32px;

    &:nth-child(2) {
      margin-left: -8px;
      z-index: 1;
    }
  }
}
</style>
