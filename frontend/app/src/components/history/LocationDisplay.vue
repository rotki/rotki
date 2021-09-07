<template>
  <location-icon
    class="location-display"
    :item="location"
    :icon="icon"
    :size="size"
  />
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { tradeLocations } from '@/components/history/consts';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocationData } from '@/components/history/type';
import AssetMixin from '@/mixins/asset-mixin';
import { TradeLocation } from '@/services/history/types';
import { SupportedBlockchains } from '@/typing/types';
import { assert } from '@/utils/assertions';

@Component({
  components: { LocationIcon }
})
export default class LocationDisplay extends Mixins(AssetMixin) {
  readonly tradeLocations = tradeLocations;
  @Prop({ required: true, type: String })
  identifier!: TradeLocation;
  @Prop({ required: false, type: Boolean, default: false })
  icon!: boolean;
  @Prop({ required: false, type: String, default: '24px' })
  size!: string;

  get location(): TradeLocationData {
    if (this.isSupportedBlockchain(this.identifier)) {
      return {
        name: this.getAssetName(this.identifier),
        identifier: this.identifier,
        exchange: false,
        imageIcon: true,
        icon: `${this.$api.serverUrl}/api/1/assets/${this.identifier}/icon`
      };
    }

    const location = tradeLocations.find(
      location => location.identifier === this.identifier
    );
    assert(!!location, 'location should not be falsy');
    return location;
  }

  private isSupportedBlockchain(identifier: string): boolean {
    return SupportedBlockchains.includes(identifier as any);
  }
}
</script>

<style scoped lang="scss">
.location-display {
  width: 100%;
}
</style>
