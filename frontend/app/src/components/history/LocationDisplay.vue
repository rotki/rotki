<template>
  <location-icon class="location-display pb-3 pt-3" :item="location" />
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { tradeLocations } from '@/components/history/consts';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocationData } from '@/components/history/type';
import { TradeLocation } from '@/services/history/types';
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

<style scoped lang="scss">
.location-display {
  width: 90px;
}
</style>
