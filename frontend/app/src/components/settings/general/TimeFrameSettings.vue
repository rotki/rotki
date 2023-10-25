<script setup lang="ts">
import {
  TimeFramePeriod,
  TimeFramePersist,
  type TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import Fragment from '@/components/helper/Fragment';

const props = defineProps<{
  message: { error: string; success: string };
  value: TimeFrameSetting;
  visibleTimeframes: TimeFramePeriod[];
  currentSessionTimeframe: TimeFrameSetting;
}>();

const emit = defineEmits<{
  (e: 'timeframe-change', timeframe: TimeFrameSetting): void;
  (e: 'visible-timeframes-change', timeframes: TimeFrameSetting[]): void;
}>();

const { message, visibleTimeframes, value, currentSessionTimeframe } =
  toRefs(props);

const timeframes = Object.values(TimeFramePeriod);
const { t } = useI18n();
const premium = usePremium();

const appendedVisibleTimeframes = computed(() => [
  TimeFramePersist.REMEMBER,
  ...get(visibleTimeframes)
]);

const invisibleTimeframes = computed(() =>
  timeframes.filter(item => !isTimeframeVisible(item))
);

const selectableTimeframes = computed(() =>
  timeframes.filter(
    item => !isTimeframeDisabled(item) && isTimeframeVisible(item)
  )
);

const text = computed<string>(() => {
  const { success, error } = get(message);
  return success ? success : error;
});

const isTimeframeVisible = (timeframe: TimeFramePeriod): boolean =>
  get(visibleTimeframes).includes(timeframe);

const isTimeframesToggleable = (timeframe: TimeFrameSetting) =>
  timeframe !== TimeFramePersist.REMEMBER;

const worksWithoutPremium = (period: TimeFrameSetting): boolean =>
  isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;

const isTimeframeDisabled = (timeframe: TimeFrameSetting) =>
  !get(premium) && !worksWithoutPremium(timeframe);

const chipClass = (timeframePeriod: TimeFrameSetting): string =>
  timeframePeriod === get(value) ? 'timeframe-settings--active' : '';

const timeframeChange = (timeframe: TimeFrameSetting) => {
  emit('timeframe-change', timeframe);
};

const visibleTimeframesChange = (timeframes: TimeFrameSetting[]) => {
  emit('visible-timeframes-change', timeframes);
};

const updateVisibleTimeframes = async (
  newTimeFrames: TimeFramePeriod[],
  replaceCurrentSessionTimeframe = false
) => {
  newTimeFrames.sort(
    (a: TimeFramePeriod, b: TimeFramePeriod) =>
      timeframes.indexOf(a) - timeframes.indexOf(b)
  );

  if (replaceCurrentSessionTimeframe) {
    const { updateSetting } = useFrontendSettingsStore();
    const { update } = useSessionSettingsStore();
    const value = newTimeFrames[0];
    update({ timeframe: value });
    await updateSetting({ lastKnownTimeframe: value });
  }

  visibleTimeframesChange(newTimeFrames);
};

const addVisibleTimeframe = async (timeframe: TimeFramePeriod) => {
  await updateVisibleTimeframes([...get(visibleTimeframes), timeframe]);
};

const removeVisibleTimeframe = async (timeframe: TimeFrameSetting) => {
  if (timeframe === get(value)) {
    timeframeChange(TimeFramePersist.REMEMBER);
  }
  await updateVisibleTimeframes(
    get(visibleTimeframes).filter(item => item !== timeframe),
    timeframe === get(currentSessionTimeframe)
  );
};
</script>

<template>
  <Fragment>
    <VRow>
      <VCol>
        <div
          class="text-h6"
          v-text="t('timeframe_settings.default_timeframe')"
        />
        <div
          class="text-subtitle-1"
          v-text="t('timeframe_settings.default_timeframe_description')"
        />
      </VCol>
    </VRow>
    <VRow align="center" justify="center">
      <VCol>
        <VCard class="pa-4" outlined>
          <div>
            <div class="text-subtitle-1">
              {{ t('timeframe_settings.visible_timeframes') }}
            </div>

            <div class="timeframe-settings">
              <VTooltip v-if="!premium" top>
                <template #activator="{ on, attrs }">
                  <VIcon small v-bind="attrs" v-on="on"> mdi-lock </VIcon>
                </template>
                <span v-text="t('overall_balances.premium_hint')" />
              </VTooltip>

              <VChip
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
              </VChip>
            </div>
          </div>

          <template v-if="invisibleTimeframes.length > 0">
            <VDivider class="my-4" />

            <div>
              <div class="text-subtitle-1">
                {{ t('timeframe_settings.inactive_timeframes') }}
              </div>
              <div class="timeframe-settings">
                <VChip
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
                </VChip>
              </div>
            </div>
          </template>
        </VCard>
      </VCol>
    </VRow>
    <VRow no-gutters>
      <VCol
        :class="{
          'success--text': !!message.success,
          'error--text': !!message.error
        }"
        class="text-subtitle-2 message"
      >
        <div v-if="text" v-text="text" />
      </VCol>
    </VRow>
  </Fragment>
</template>

<style scoped lang="scss">
.timeframe-settings {
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
