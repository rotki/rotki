<script setup lang="ts">
import { displayDateFormatter } from '@/data/date-formatter';
import { DateFormat } from '@/types/date-format';

const rootAttrs = useAttrs();

const selections = [
  {
    value: DateFormat.DateMonthYearHourMinuteSecond,
  },
  {
    value: DateFormat.MonthDateYearHourMinuteSecond,
  },
  {
    value: DateFormat.YearMonthDateHourMinuteSecond,
  },
];

function dateInputFormatExample(format: DateFormat): string {
  return displayDateFormatter.format(new Date(), format);
}

const { t } = useI18n();
</script>

<template>
  <VSelect
    v-bind="rootAttrs"
    item-title="value"
    item-value="value"
    variant="outlined"
    persistent-hint
    :items="selections"
  >
    <template #item="{ item, props }">
      <ListItem
        no-hover
        no-padding
        v-bind="props"
        :title="item.value"
        :subtitle="
          t('general_settings.date_input_format_hint', {
            format: dateInputFormatExample(item.value),
          })
        "
      />
    </template>
  </VSelect>
</template>
