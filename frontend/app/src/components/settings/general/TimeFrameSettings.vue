<template>
  <fragment>
    <v-row>
      <v-col>
        <div
          class="text-h6"
          v-text="t('timeframe_settings.default_timeframe')"
        />
        <div
          class="text-subtitle-1"
          v-text="t('timeframe_settings.default_timeframe_description')"
        />
      </v-col>
    </v-row>
    <v-row align="center" justify="center">
      <v-col>
        <v-card class="pa-4" outlined>
          <div>
            <div class="text-subtitle-1">
              {{ t('timeframe_settings.visible_timeframes') }}
            </div>

            <div class="timeframe-settings">
              <v-tooltip v-if="!premium" top>
                <template #activator="{ on, attrs }">
                  <v-icon small v-bind="attrs" v-on="on"> mdi-lock </v-icon>
                </template>
                <span v-text="t('overall_balances.premium_hint')" />
              </v-tooltip>

              <v-chip
                v-for="(timeframe, i) in appendedVisibleTimeframes"
                :key="i"
                :class="chipClass(timeframe)"
                class="ma-2"
                small
                :close="
                  isTimeframesToggleable(timeframe) &&
                  !isTimeframeDisabled(timeframe) &&
                  selectableTimeframes.length > 1
                "
                :disabled="isTimeframeDisabled(timeframe)"
                @click:close="removeVisibleTimeframe(timeframe)"
                @click="timeframeChange(timeframe)"
              >
                {{ timeframe }}
              </v-chip>
            </div>
          </div>

          <template v-if="invisibleTimeframes.length > 0">
            <v-divider class="my-4" />

            <div>
              <div class="text-subtitle-1">
                {{ t('timeframe_settings.inactive_timeframes') }}
              </div>
              <div class="timeframe-settings">
                <v-chip
                  v-for="(timeframe, i) in invisibleTimeframes"
                  :key="i"
                  class="ma-2"
                  small
                  close-icon="mdi-plus"
                  :close="isTimeframesToggleable(timeframe)"
                  :disabled="isTimeframeDisabled(timeframe)"
                  @click:close="addVisibleTimeframe(timeframe)"
                  @click="addVisibleTimeframe(timeframe)"
                >
                  {{ timeframe }}
                </v-chip>
              </div>
            </div>
          </template>
        </v-card>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col
        :class="{
          'success--text': !!message.success,
          'error--text': !!message.error
        }"
        class="text-subtitle-2 message"
      >
        <div v-if="text" v-text="text" />
      </v-col>
    </v-row>
  </fragment>
</template>

<script lang="ts">
import {
  TimeFramePeriod,
  TimeFramePersist,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { get } from '@vueuse/core';
import { computed, defineComponent, PropType, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import Fragment from '@/components/helper/Fragment';
import { getPremium } from '@/composables/session';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';
import { isPeriodAllowed } from '@/store/settings/utils';

const validator = (value: any) =>
  Object.values(TimeFramePeriod).includes(value) ||
  value === TimeFramePersist.REMEMBER;

export default defineComponent({
  name: 'TimeFrameSettings',
  components: { Fragment },
  props: {
    message: {
      required: true,
      type: Object as PropType<{ error: string; success: string }>
    },
    value: {
      required: true,
      type: String,
      validator
    },
    visibleTimeframes: {
      required: true,
      type: Array as PropType<TimeFramePeriod[]>
    },
    currentSessionTimeframe: {
      required: true,
      type: String as PropType<TimeFramePeriod>,
      validator
    }
  },
  emits: ['timeframe-change', 'visible-timeframes-change'],
  setup(props, { emit }) {
    const { t } = useI18n();
    const { message, visibleTimeframes, value, currentSessionTimeframe } =
      toRefs(props);

    const appendedVisibleTimeframes = computed(() => {
      return [TimeFramePersist.REMEMBER, ...get(visibleTimeframes)];
    });

    const timeframes = Object.values(TimeFramePeriod);

    const invisibleTimeframes = computed(() => {
      return timeframes.filter(item => {
        return !isTimeframeVisible(item);
      });
    });

    const isTimeframeVisible = (timeframe: TimeFramePeriod): boolean => {
      return get(visibleTimeframes).includes(timeframe);
    };

    const isTimeframesToggleable = (timeframe: TimeFrameSetting) => {
      return timeframe !== TimeFramePersist.REMEMBER;
    };

    const premium = getPremium();

    const worksWithoutPremium = (period: TimeFrameSetting): boolean => {
      return isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;
    };

    const isTimeframeDisabled = (timeframe: TimeFrameSetting) => {
      return !get(premium) && !worksWithoutPremium(timeframe);
    };

    const selectableTimeframes = computed(() => {
      return timeframes.filter(item => {
        return !isTimeframeDisabled(item) && isTimeframeVisible(item);
      });
    });

    const text = computed<string>(() => {
      const { success, error } = get(message);
      return success ? success : error;
    });

    const chipClass = (timeframePeriod: TimeFrameSetting): string => {
      return timeframePeriod === get(value) ? 'timeframe-settings--active' : '';
    };

    const visibleTimeframesChange = (_timeframes: TimeFrameSetting[]) => {
      emit('visible-timeframes-change', _timeframes);
    };

    const updateVisibleTimeframes = async (
      newTimeFrames: TimeFramePeriod[],
      replaceCurrentSessionTimeframe: boolean = false
    ) => {
      newTimeFrames.sort((a: TimeFramePeriod, b: TimeFramePeriod) => {
        return timeframes.indexOf(a) - timeframes.indexOf(b);
      });

      if (replaceCurrentSessionTimeframe) {
        const { updateSetting } = useFrontendSettingsStore();
        const { update } = useSessionSettingsStore();
        const value = newTimeFrames[0];
        await update({ timeframe: value });
        await updateSetting({ lastKnownTimeframe: value });
      }

      visibleTimeframesChange(newTimeFrames);
    };

    const addVisibleTimeframe = async (timeframe: TimeFramePeriod) => {
      await updateVisibleTimeframes([...get(visibleTimeframes), timeframe]);
    };

    const timeframeChange = (_timeframe: TimeFrameSetting) => {
      emit('timeframe-change', _timeframe);
    };

    const removeVisibleTimeframe = async (timeframe: TimeFrameSetting) => {
      if (timeframe === get(value)) {
        timeframeChange(TimeFramePersist.REMEMBER);
      }
      await updateVisibleTimeframes(
        get(visibleTimeframes).filter(item => {
          return item !== timeframe;
        }),
        timeframe === get(currentSessionTimeframe)
      );
    };

    return {
      t,
      premium,
      appendedVisibleTimeframes,
      chipClass,
      isTimeframesToggleable,
      isTimeframeDisabled,
      selectableTimeframes,
      removeVisibleTimeframe,
      timeframeChange,
      invisibleTimeframes,
      addVisibleTimeframe,
      text
    };
  }
});
</script>
<style scoped lang="scss">
.timeframe-settings {
  ::v-deep {
    .v-chip {
      cursor: pointer;
    }
  }

  &--active {
    color: white !important;
    background-color: var(--v-primary-base) !important;
  }
}

.message {
  padding-top: 0.5rem !important;
  height: 1rem;
}
</style>
