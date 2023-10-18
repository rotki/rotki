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

const css = useCssModule();

const { timestamp, showTimezone, noTime, milliseconds } = toRefs(props);
const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());

const dateDisplayFormatWithMilliseconds: ComputedRef<string> = computed(() => {
  const format = get(dateDisplayFormat);
  if (!get(milliseconds)) {
    return format;
  }

  const millisecondFormat = '%s';

  if (format.includes(millisecondFormat)) {
    return format;
  }

  return format
    .replace('%S', `%S.${millisecondFormat}`)
    .replace('%-S', `%-S.${millisecondFormat}`);
});

const dateFormat = computed<string>(() => {
  const display = get(showTimezone)
    ? get(dateDisplayFormatWithMilliseconds)
    : get(dateDisplayFormatWithMilliseconds)
        .replace('%z', '')
        .replace('%Z', '');

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
const formattedDateWithTimezone = format(
  date,
  dateDisplayFormatWithMilliseconds
);

const showTooltip = computed(() => {
  const timezone = get(showTimezone);
  const format = get(dateDisplayFormatWithMilliseconds);
  return !timezone && (format.includes('%z') || format.includes('%Z'));
});

const splittedByMillisecondsPart = computed(() =>
  get(formattedDate).split('.')
);
</script>

<template>
  <span>
    <RuiTooltip
      :popper="{ placement: 'top' }"
      open-delay="400"
      :disabled="!showTooltip"
    >
      <template #activator="{ on, attrs }">
        <span
          class="date-display whitespace-none"
          :class="{ [css.blur]: !shouldShowAmount }"
          v-bind="attrs"
          v-on="on"
        >
          <span>{{ splittedByMillisecondsPart[0] }}</span>
          <span
            v-if="milliseconds && splittedByMillisecondsPart[1]"
            class="text-[0.625rem]"
          >
            .{{ splittedByMillisecondsPart[1] }}
          </span>
        </span>
      </template>
      <span> {{ formattedDateWithTimezone }} </span>
    </RuiTooltip>
  </span>
</template>

<style module lang="scss">
.blur {
  filter: blur(0.75em);
}
</style>
