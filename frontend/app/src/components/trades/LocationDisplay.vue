<template>
  <location-icon :item="location" />
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { tradeLocations } from '@/components/trades/consts';
import LocationIcon from '@/components/trades/LocationIcon.vue';
import { TradeLocationData } from '@/components/trades/type';
import { TradeLocation } from '@/services/trades/types';
import { assert } from '@/utils/assertions';

@Component({
  components: { LocationIcon }
})
export default class LocationDisplay extends Vue {
  readonly tradeLocations = tradeLocations;
  @Prop({ required: true, type: String })
  identifier!: TradeLocation;

  get location(): TradeLocationData {
    const location = tradeLocations.find(
      location => location.identifier === this.identifier
    );
    assert(!!location, 'location should not be falsy');
    return location;
  }
}
</script>
