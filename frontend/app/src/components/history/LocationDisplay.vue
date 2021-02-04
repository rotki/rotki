<template>
  <location-icon class="location-display pb-3 pt-3" :item="location" />
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { tradeLocations } from '@/components/history/consts';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocationData } from '@/components/history/type';
import { TradeLocation } from '@/services/history/types';
import { SupportedAsset } from '@/services/types-model';
import { SupportedBlockchains } from '@/typing/types';
import { assert } from '@/utils/assertions';

@Component({
  components: { LocationIcon },
  computed: {
    ...mapGetters('balances', ['assetInfo'])
  }
})
export default class LocationDisplay extends Vue {
  readonly tradeLocations = tradeLocations;
  @Prop({ required: true, type: String })
  identifier!: TradeLocation;

  assetInfo!: (key: string) => SupportedAsset;

  get location(): TradeLocationData {
    if (this.isSupportedBlockchain(this.identifier)) {
      return {
        name: this.assetInfo(this.identifier).name ?? '',
        identifier: this.identifier,
        exchange: false,
        imageIcon: true,
        icon: `${process.env.VUE_APP_BACKEND_URL}/api/1/assets/${this.identifier}/icon/small`
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
  width: 90px;
}
</style>
