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
    <RuiCardHeader class="p-0 mb-4">
      <template #header>
        {{ t('timeframe_settings.default_timeframe') }}
      </template>
      <template #subheader>
        {{ t('timeframe_settings.default_timeframe_description') }}
      </template>
    </RuiCardHeader>
    <RuiCard>
      <div class="text-subtitle-1">
        {{ t('timeframe_settings.visible_timeframes') }}
      </div>

      <div class="flex items-center gap-3" :class="{ 'mt-2': premium }">
        <PremiumLock
          v-if="!premium"
          :tooltip="t('overall_balances.premium_hint')"
        />
        <RuiChip
          v-for="(timeframe, i) in appendedVisibleTimeframes"
          :key="i"
          :color="timeframe === value ? 'primary' : 'grey'"
          size="sm"
          clickable
          :closeable="
            isTimeframesToggleable(timeframe) &&
            !isTimeframeDisabled(timeframe) &&
            selectableTimeframes.length > 1
          "
          :disabled="isTimeframeDisabled(timeframe)"
          @click:close="removeVisibleTimeframe(timeframe)"
          @click="timeframeChange(timeframe)"
        >
          {{ timeframe }}
        </RuiChip>
      </div>

      <template v-if="invisibleTimeframes.length > 0">
        <RuiDivider class="my-4" />

        <div class="text-subtitle-1">
          {{ t('timeframe_settings.inactive_timeframes') }}
        </div>
        <div class="flex items-center gap-3 mt-2">
          <RuiChip
            v-for="(timeframe, i) in invisibleTimeframes"
            :key="i"
            size="sm"
            close-icon="add-circle-line"
            closeable
            clickable
            :close="isTimeframesToggleable(timeframe)"
            :disabled="isTimeframeDisabled(timeframe)"
            @click:close="addVisibleTimeframe(timeframe)"
            @click="addVisibleTimeframe(timeframe)"
          >
            {{ timeframe }}
          </RuiChip>
        </div>
      </template>
    </RuiCard>
    <div
      :class="{
        'text-rui-success': !!message.success,
        'text-rui-error': !!message.error
      }"
      class="text-caption pt-1 pl-3 min-h-[1.5rem]"
    >
      <div v-if="text">{{ text }}</div>
    </div>
  </Fragment>
</template>
