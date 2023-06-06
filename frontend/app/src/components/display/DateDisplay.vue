<script setup lang="ts">
import { displayDateFormatter } from '@/data/date_formatter';

const props = withDefaults(
  defineProps<{
    timestamp: number;
    showTimezone?: boolean;
    noTime?: boolean;
  }>(),
  {
    showTimezone: false,
    noTime: false
  }
);

const { timestamp, showTimezone, noTime } = toRefs(props);
const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
const { scrambleData, shouldShowAmount } = storeToRefs(
  useSessionSettingsStore()
);

const dateFormat = computed<string>(() => {
  const display = get(showTimezone)
    ? get(dateDisplayFormat)
    : get(dateDisplayFormat).replace('%z', '').replace('%Z', '');

  if (get(noTime)) {
    return display.split(' ')[0];
  }
  return display;
});

const displayTimestamp = computed<number>(() => {
  if (!get(scrambleData)) {
    return get(timestamp);
  }
  const start = new Date(2016, 0, 1).getTime();
  const now = Date.now();
  return new Date(start + Math.random() * (now - start)).getTime() / 1000;
});

const date = computed(() => new Date(get(displayTimestamp) * 1000));
const format = (date: Ref<Date>, format: Ref<string>) =>
  computed(() => displayDateFormatter.format(get(date), get(format)));

const formattedDate = format(date, dateFormat);
const formattedDateWithTimezone = format(date, dateDisplayFormat);

const showTooltip = computed(() => {
  const timezone = get(showTimezone);
  const format = get(dateDisplayFormat);
  return !timezone && (format.includes('%z') || format.includes('%Z'));
});
</script>

<template>
  <v-tooltip top open-delay="400" :disabled="!showTooltip">
    <template #activator="{ on, attrs }">
      <span
        class="date-display"
        :class="{ 'blur-content': !shouldShowAmount }"
        v-bind="attrs"
        v-on="on"
      >
        {{ formattedDate }}
      </span>
    </template>
    <span> {{ formattedDateWithTimezone }} </span>
  </v-tooltip>
</template>

<style scoped lang="scss">
.blur-content {
  filter: blur(0.75em);
}
</style>
