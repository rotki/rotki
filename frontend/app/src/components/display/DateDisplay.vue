<script setup lang="ts">
import { displayDateFormatter } from '@/data/date_formatter';

const props = withDefaults(
  defineProps<{
    timestamp: number;
    showTimezone?: boolean;
    noTime?: boolean;
    milliseconds?: boolean;
  }>(),
  {
    showTimezone: false,
    noTime: false,
    milliseconds: false
  }
);

const { timestamp, showTimezone, noTime, milliseconds } = toRefs(props);
const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());

const dateFormat = computed<string>(() => {
  const display = get(showTimezone)
    ? get(dateDisplayFormat)
    : get(dateDisplayFormat).replace('%z', '').replace('%Z', '').trim();

  if (get(noTime)) {
    return display.split(' ')[0];
  }
  return display;
});

const { scrambleTimestamp } = useScramble();

const reactiveScramble = reactify(scrambleTimestamp);
const displayTimestamp = reactiveScramble(timestamp, milliseconds);

const date = computed(() => {
  const display = get(displayTimestamp);
  return new Date(get(milliseconds) ? display : display * 1000);
});

const format = (date: Ref<Date>, format: Ref<string>) =>
  computed(() => displayDateFormatter.format(get(date), get(format)));

const formattedDate = format(date, dateFormat);
const formattedDateWithTimezone = format(date, dateDisplayFormat);

const showTooltip = computed(() => {
  const timezone = get(showTimezone);
  const format = get(dateDisplayFormat);
  return !timezone && (format.includes('%z') || format.includes('%Z'));
});

const splittedByMillisecondsPart = computed(() =>
  get(formattedDate).split('.')
);

const { copy, copied } = useCopy(formattedDate);
</script>

<template>
  <CopyTooltip
    class="items-baseline"
    :copied="copied"
    :tooltip="showTooltip ? formattedDateWithTimezone : null"
    :class="{ blur: !shouldShowAmount }"
    @click="copy()"
  >
    {{ splittedByMillisecondsPart[0] }}
    <span v-if="splittedByMillisecondsPart[1]" class="text-[0.625rem]">
      .{{ splittedByMillisecondsPart[1] }}
    </span>
  </CopyTooltip>
</template>
