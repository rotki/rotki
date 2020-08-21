<template>
  <v-row>
    <v-col cols="12">
      <v-card>
        <div class="mx-4 py-2">
          <v-autocomplete
            :value="value"
            :items="tradeLocations"
            hide-details
            hide-selected
            hide-no-data
            clearable
            :label="$t('trade_location_selector.label')"
            item-text="name"
            item-value="identifier"
            @input="input"
          >
            <template #selection="{ item }">
              <location-icon :item="item" />
            </template>
            <template #item="{ item }">
              <location-icon :item="item" />
            </template>
          </v-autocomplete>
        </div>
        <v-card-text>
          {{
            $tc('trade_location_selector.selection', {
              location: value
            })
          }}
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import LocationIcon from '@/components/trades/LocationIcon.vue';
import { TradeLocationData, TradeLocation } from '@/components/trades/type';

@Component({
  components: { LocationIcon }
})
export default class TradeLocationSelector extends Vue {
  readonly tradeLocations: TradeLocationData[] = [
    {
      identifier: 'kraken',
      name: 'Kraken',
      icon: require('@/assets/images/kraken.png')
    },
    {
      identifier: 'bittrex',
      name: 'Bittrex',
      icon: require('@/assets/images/bittrex.png')
    },
    {
      identifier: 'binance',
      name: 'Binance',
      icon: require('@/assets/images/binance.png')
    },
    {
      identifier: 'gemini',
      name: 'Gemini',
      icon: require('@/assets/images/gemini.png')
    },
    {
      identifier: 'external',
      name: 'External'
    }
  ];

  @Prop({ required: true })
  value!: TradeLocation;

  @Emit()
  input(_value: TradeLocation) {}
}
</script>
