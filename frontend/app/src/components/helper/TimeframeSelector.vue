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
      v-for="(timeframe, i) in visibleTimeframes"
      :key="i"
      :class="activeClass(timeframe)"
      class="ma-2"
      :disabled="(!premium && !worksWithoutPremium(timeframe)) || disabled"
      small
      @click="input(timeframe)"
    >
      {{ timeframe }}
    </v-chip>
  </div>
</template>

<script lang="ts">
import {
  TimeFramePersist,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { Component, Emit, Mixins, Prop } from 'vue-property-decorator';
import PremiumMixin from '@/mixins/premium-mixin';

import { isPeriodAllowed } from '@/store/settings/utils';

@Component({})
export default class TimeframeSelector extends Mixins(PremiumMixin) {
  @Prop({ required: true, type: String })
  value!: TimeFrameSetting;
  @Prop({ required: false, type: Boolean, default: false })
  disabled!: boolean;
  @Prop({ required: true, type: Array })
  visibleTimeframes!: TimeFrameSetting[];

  @Emit()
  input(_value: TimeFrameSetting) {}

  worksWithoutPremium(period: TimeFrameSetting): boolean {
    return isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;
  }

  activeClass(timeframePeriod: TimeFrameSetting): string {
    return timeframePeriod === this.value ? 'timeframe-selector--active' : '';
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
