<template>
  <v-row>
    <v-col cols="12">
      <v-card>
        <div class="mx-4 py-2">
          <v-autocomplete
            :value="value"
            :items="locations"
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
              <location-icon horizontal :item="item" />
            </template>
            <template #item="{ item }">
              <location-icon horizontal :item="item" />
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
import { tradeLocations } from '@/components/history/consts';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocation } from '@/services/history/types';

@Component({
  components: { LocationIcon }
})
export default class TradeLocationSelector extends Vue {
  readonly tradeLocations = tradeLocations;

  get locations(): TradeLocation[] {
    return this.showExternal
      ? tradeLocations
      : tradeLocations.filter(location => location.identifier !== 'external');
  }

  get name(): string {
    return (
      this.tradeLocations.find(location => location.identifier === this.value)
        ?.name ?? ''
    );
  }

  @Prop({ required: true })
  value!: TradeLocation;

  @Prop({ required: false, type: Boolean, default: false })
  showExternal!: boolean;

  @Emit()
  input(_value: TradeLocation) {}
}
</script>
