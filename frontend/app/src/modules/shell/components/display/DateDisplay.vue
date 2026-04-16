<script setup lang="ts">
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useScramble } from '@/modules/settings/use-scramble';
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';

const { hideTooltip = false, milliseconds = false, noTime = false, showTimezone = false, timestamp } = defineProps<{
  timestamp: number | string;
  showTimezone?: boolean;
  noTime?: boolean;
  milliseconds?: boolean;
  hideTooltip?: boolean;
}>();

const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

const dateFormat = computed<string>(() => {
  const display = showTimezone
    ? get(dateDisplayFormat)
    : get(dateDisplayFormat).replace('%z', '').replace('%Z', '').trim();

  if (noTime)
    return display.split(' ')[0];

  return display;
});

const { scrambleTimestamp, shouldShowAmount } = useScramble();

const numericTimestamp = useToNumber(() => timestamp);
const reactiveScramble = reactify(scrambleTimestamp);
const displayTimestamp = reactiveScramble(numericTimestamp, () => milliseconds);

const date = computed<Date>(() => {
  const display = get(displayTimestamp);
  return new Date(milliseconds ? display : display * 1000);
});

function format(date: Ref<Date>, format: Ref<string>): ComputedRef<string> {
  return computed<string>(() => displayDateFormatter.format(get(date), get(format)));
}

const formattedDate = format(date, dateFormat);
const formattedDateWithTimezone = format(date, dateDisplayFormat);

const showTooltip = computed<boolean>(() => {
  const format = get(dateDisplayFormat);
  return !showTimezone && (format.includes('%z') || format.includes('%Z'));
});

const splitByMillisecondsPart = computed<string[]>(() => get(formattedDate).split('.'));
</script>

<template>
  <CopyTooltip
    class="items-baseline"
    :tooltip="showTooltip ? formattedDateWithTimezone : null"
    :class="{ blur: !shouldShowAmount }"
    :disabled="hideTooltip"
    :value="formattedDate"
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
