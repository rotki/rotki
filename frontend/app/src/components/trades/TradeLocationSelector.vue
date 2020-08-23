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
            !value
              ? $t('trade_location_selector.selection-none')
              : $t('trade_location_selector.selection-single', {
                  location: name
                })
          }}
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { tradeLocations } from '@/components/trades/consts';
import LocationIcon from '@/components/trades/LocationIcon.vue';
import { TradeLocation } from '@/components/trades/type';

@Component({
  components: { LocationIcon }
})
export default class TradeLocationSelector extends Vue {
  readonly tradeLocations = tradeLocations;

  get name(): string {
    return (
      this.tradeLocations.find(location => location.identifier === this.value)
        ?.name ?? ''
    );
  }

  @Prop({ required: true })
  value!: TradeLocation;

  @Emit()
  input(_value: TradeLocation) {}
}
</script>
