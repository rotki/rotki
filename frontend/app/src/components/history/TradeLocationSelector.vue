<template>
  <v-row>
    <v-col cols="12">
      <v-card :flat="outlined">
        <div class="mx-4 py-2" :class="outlined ? 'px-3' : null">
          <v-autocomplete
            :value="value"
            :items="locations"
            hide-details
            hide-selected
            hide-no-data
            clearable
            chips
            :class="outlined ? 'trade-location-selector--outlined' : null"
            :outlined="outlined"
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
              ? $t('trade_location_selector.selection_none')
              : $t('trade_location_selector.selection_single', {
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
import { TradeLocationData } from '@/components/history/type';
import { TradeLocation } from '@/services/history/types';

@Component({
  components: { LocationIcon }
})
export default class TradeLocationSelector extends Vue {
  readonly tradeLocations = tradeLocations;

  get locations(): TradeLocationData[] {
    return tradeLocations.filter(location =>
      this.availableLocations.includes(location.identifier)
    );
  }

  get name(): string {
    return (
      this.tradeLocations.find(location => location.identifier === this.value)
        ?.name ?? ''
    );
  }

  @Prop({ required: true })
  value!: TradeLocation;

  @Prop({ required: false, type: Array, default: () => [] })
  availableLocations!: TradeLocation[];
  @Prop({ required: false, default: false, type: Boolean })
  outlined!: boolean;

  @Emit()
  input(_value: TradeLocation) {}
}
</script>

<style scoped lang="scss">
.trade-location-selector {
  &--outlined {
    ::v-deep {
      /* stylelint-disable */
      .v-label:not(.v-label--active) {
        /* stylelint-enable */
        top: 24px;
      }

      .v-input {
        &__icon {
          &--clear {
            margin-top: 6px;
          }

          &--append {
            margin-top: 6px;
          }
        }
      }
    }
  }
}
</style>
