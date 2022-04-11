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
import { defineComponent, PropType, toRefs } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { getPremium } from '@/composables/session';

import { isPeriodAllowed } from '@/store/settings/utils';

export default defineComponent({
  name: 'TimeframeSelector',
  props: {
    value: { required: true, type: String as PropType<TimeFrameSetting> },
    disabled: { required: false, type: Boolean, default: false },
    visibleTimeframes: { required: true, type: Array }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { value } = toRefs(props);
    const input = (_value: TimeFrameSetting) => {
      emit('input', _value);
    };

    const premium = getPremium();

    const worksWithoutPremium = (period: TimeFrameSetting): boolean => {
      return isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;
    };

    const activeClass = (timeframePeriod: TimeFrameSetting): string => {
      return timeframePeriod === get(value) ? 'timeframe-selector--active' : '';
    };

    return {
      input,
      premium,
      worksWithoutPremium,
      activeClass
    };
  }
});
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
