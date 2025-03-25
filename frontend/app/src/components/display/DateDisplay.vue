<script setup lang="ts">
import CopyTooltip from '@/components/helper/CopyTooltip.vue';
import { useCopy } from '@/composables/copy';
import { useScramble } from '@/composables/scramble';
import { displayDateFormatter } from '@/data/date-formatter';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';

const props = withDefaults(
  defineProps<{
    timestamp: number | string;
    showTimezone?: boolean;
    noTime?: boolean;
    milliseconds?: boolean;
    hideTooltip?: boolean;
  }>(),
  {
    hideTooltip: false,
    milliseconds: false,
    noTime: false,
    showTimezone: false,
  },
);

const { milliseconds, noTime, showTimezone, timestamp } = toRefs(props);
const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());

const dateFormat = computed<string>(() => {
  const display = get(showTimezone) ? get(dateDisplayFormat) : get(dateDisplayFormat).replace('%z', '').replace('%Z', '').trim();

  if (get(noTime))
    return display.split(' ')[0];

  return display;
});

const { scrambleTimestamp } = useScramble();

const numericTimestamp = useToNumber(timestamp);
const reactiveScramble = reactify(scrambleTimestamp);
const displayTimestamp = reactiveScramble(numericTimestamp, milliseconds);

const date = computed(() => {
  const display = get(displayTimestamp);
  return new Date(get(milliseconds) ? display : display * 1000);
});

function format(date: Ref<Date>, format: Ref<string>) {
  return computed(() => displayDateFormatter.format(get(date), get(format)));
}

const formattedDate = format(date, dateFormat);
const formattedDateWithTimezone = format(date, dateDisplayFormat);

const showTooltip = computed(() => {
  const timezone = get(showTimezone);
  const format = get(dateDisplayFormat);
  return !timezone && (format.includes('%z') || format.includes('%Z'));
});

const splitByMillisecondsPart = computed(() => get(formattedDate).split('.'));

const { copied, copy } = useCopy(formattedDate);
</script>

<template>
  <CopyTooltip
    class="items-baseline"
    :copied="copied"
    :tooltip="showTooltip ? formattedDateWithTimezone : null"
    :class="{ blur: !shouldShowAmount }"
    :disabled="hideTooltip"
    @click="copy()"
  >
    {{ splitByMillisecondsPart[0] }}
    <span
      v-if="splitByMillisecondsPart[1]"
      class="text-[0.625rem]"
    >
      .{{ splitByMillisecondsPart[1] }}
    </span>
  </CopyTooltip>
</template>
