<script setup lang="ts">
import { TimeFramePeriod, TimeFramePersist, type TimeFrameSetting } from '@rotki/common';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { usePremium } from '@/composables/premium';
import { isPeriodAllowed } from '@/modules/settings/settings-utils';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import { useSessionSettingsStore } from '@/store/settings/session';

const { currentSessionTimeframe, message, value, visibleTimeframes } = defineProps<{
  message: { error: string; success: string };
  value: TimeFrameSetting;
  visibleTimeframes: TimeFramePeriod[];
  currentSessionTimeframe: TimeFrameSetting;
}>();

const emit = defineEmits<{
  'timeframe-change': [timeframe: TimeFrameSetting];
  'visible-timeframes-change': [timeframes: TimeFrameSetting[]];
}>();

const timeframes = Object.values(TimeFramePeriod);
const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();

const appendedVisibleTimeframes = computed(() => [TimeFramePersist.REMEMBER, ...visibleTimeframes]);

const invisibleTimeframes = computed(() => timeframes.filter(item => !isTimeframeVisible(item)));

const selectableTimeframes = computed(() =>
  timeframes.filter(item => !isTimeframeDisabled(item) && isTimeframeVisible(item)),
);

const text = computed<string>(() => {
  const { error, success } = message;
  return success || error;
});

function isTimeframeVisible(timeframe: TimeFramePeriod): boolean {
  return visibleTimeframes.includes(timeframe);
}

function isTimeframesToggleable(timeframe: TimeFrameSetting) {
  return timeframe !== TimeFramePersist.REMEMBER;
}

function worksWithoutPremium(period: TimeFrameSetting): boolean {
  return isPeriodAllowed(period) || period === TimeFramePersist.REMEMBER;
}

function isTimeframeDisabled(timeframe: TimeFrameSetting) {
  return !get(premium) && !worksWithoutPremium(timeframe);
}

function timeframeChange(timeframe: TimeFrameSetting) {
  emit('timeframe-change', timeframe);
}

function visibleTimeframesChange(timeframes: TimeFrameSetting[]) {
  emit('visible-timeframes-change', timeframes);
}

async function updateVisibleTimeframes(newTimeFrames: TimeFramePeriod[], replaceCurrentSessionTimeframe = false) {
  newTimeFrames.sort((a: TimeFramePeriod, b: TimeFramePeriod) => timeframes.indexOf(a) - timeframes.indexOf(b));

  if (replaceCurrentSessionTimeframe) {
    const { updateFrontendSetting } = useSettingsOperations();
    const { update } = useSessionSettingsStore();
    const value = newTimeFrames[0];
    update({ timeframe: value });
    await updateFrontendSetting({ lastKnownTimeframe: value });
  }

  visibleTimeframesChange(newTimeFrames);
}

async function addVisibleTimeframe(timeframe: TimeFramePeriod) {
  await updateVisibleTimeframes([...visibleTimeframes, timeframe]);
}

async function removeVisibleTimeframe(timeframe: TimeFrameSetting) {
  if (timeframe === value)
    timeframeChange(TimeFramePersist.REMEMBER);

  await updateVisibleTimeframes(
    visibleTimeframes.filter(item => item !== timeframe),
    timeframe === currentSessionTimeframe,
  );
}
</script>

<template>
  <RuiCard class="h-auto">
    <div class="font-medium">
      {{ t('timeframe_settings.visible_timeframes') }}
    </div>

    <div
      class="flex flex-wrap items-center gap-3"
      :class="{ 'mt-2': premium }"
    >
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
          isTimeframesToggleable(timeframe) && !isTimeframeDisabled(timeframe) && selectableTimeframes.length > 1
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

      <div class="font-medium">
        {{ t('timeframe_settings.inactive_timeframes') }}
      </div>
      <div class="flex flex-wrap items-center gap-3 mt-2">
        <RuiChip
          v-for="(timeframe, i) in invisibleTimeframes"
          :key="i"
          size="sm"
          close-icon="lu-circle-plus"
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
      'text-rui-error': !!message.error,
    }"
    class="text-caption pt-1 pl-3 min-h-[1.5rem]"
  >
    <div v-if="text">
      {{ text }}
    </div>
  </div>
</template>
