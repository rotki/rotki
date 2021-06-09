<template>
  <v-autocomplete
    v-bind="$attrs"
    :value="value"
    :disabled="pending"
    :items="locations"
    item-value="identifier"
    item-text="name"
    @input="change"
    v-on="$listeners"
  >
    <template #item="{ item, attrs, on }">
      <location-icon
        :id="`balance-location__${item.identifier}`"
        v-bind="attrs"
        horizontal
        :item="item"
        no-padding
        v-on="on"
      />
    </template>
    <template #selection="{ item, attrs, on }">
      <location-icon
        v-bind="attrs"
        horizontal
        :item="item"
        no-padding
        v-on="on"
      />
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { tradeLocations } from '@/components/history/consts';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocationData } from '@/components/history/type';

@Component({
  components: { LocationIcon }
})
export default class LocationSelector extends Vue {
  @Prop({ required: true })
  value!: string | null;
  @Prop({ required: false, type: Boolean, default: false })
  pending!: boolean;

  @Emit()
  change(_value: string) {}

  get locations(): TradeLocationData[] {
    return tradeLocations;
  }
}
</script>

<style scoped lang="scss"></style>
