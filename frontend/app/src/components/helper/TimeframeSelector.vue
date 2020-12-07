<template>
  <div class="timeframe-selector text-center">
    <v-tooltip v-if="!premium" top>
      <template #activator="{ on, attrs }">
        <v-icon
          class="timeframe-selector__premium"
          small
          v-bind="attrs"
          v-on="on"
        >
          mdi-lock
        </v-icon>
      </template>
      <span v-text="$t('overall_balances.premium_hint')" />
    </v-tooltip>
    <v-chip
      v-for="(timeframe, i) in timeframes"
      :key="i"
      :class="activeClass(timeframe.text)"
      class="ma-2"
      :disabled="!premium && !worksWithoutPremium(timeframe.text)"
      small
      @click="clicked(timeframe.text)"
    >
      {{ timeframe.text }}
    </v-chip>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import {
  TIMEFRAME_TWO_WEEKS,
  TIMEFRAME_WEEK,
  timeframes
} from '@/components/dashboard/const';
import { TimeFramePeriod, Timeframes } from '@/components/dashboard/types';
import PremiumMixin from '@/mixins/premium-mixin';

@Component({})
export default class TimeframeSelector extends Mixins(PremiumMixin) {
  @Prop({ required: true, type: String })
  value!: TimeFramePeriod;

  @Emit()
  input(_value: TimeFramePeriod) {}

  @Emit()
  changed(_value: TimeFramePeriod) {}

  clicked(value: TimeFramePeriod) {
    this.input(value);
    this.changed(value);
  }

  worksWithoutPremium(period: TimeFramePeriod): boolean {
    return [TIMEFRAME_WEEK, TIMEFRAME_TWO_WEEKS].includes(period);
  }

  activeClass(timeframePeriod: TimeFramePeriod): string {
    return timeframePeriod === this.value ? 'timeframe-selector--active' : '';
  }

  get timeframes(): Timeframes {
    return timeframes;
  }
}
</script>

<style scoped lang="scss">
.timeframe-selector {
  ::v-deep {
    .v-chip {
      cursor: pointer;
    }
  }

  &--active {
    color: white !important;
    background-color: var(--v-primary-base) !important;
  }

  &__premium {
    margin-left: -16px;
  }
}
</style>
