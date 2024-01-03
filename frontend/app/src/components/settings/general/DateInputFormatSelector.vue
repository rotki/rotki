<script setup lang="ts">
import { displayDateFormatter } from '@/data/date_formatter';
import { DateFormat } from '@/types/date-format';

const rootAttrs = useAttrs();

const selections = [
  {
    value: DateFormat.DateMonthYearHourMinuteSecond
  },
  {
    value: DateFormat.MonthDateYearHourMinuteSecond
  },
  {
    value: DateFormat.YearMonthDateHourMinuteSecond
  }
];

const dateInputFormatExample = (format: DateFormat): string =>
  displayDateFormatter.format(new Date(), format);

const { t } = useI18n();
</script>

<template>
  <VSelect
    v-bind="rootAttrs"
    item-text="value"
    item-value="value"
    outlined
    persistent-hint
    :items="selections"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #item="{ item, attrs, on }">
      <ListItem
        no-hover
        no-padding
        v-bind="attrs"
        :title="item.value"
        :subtitle="
          t('general_settings.date_input_format_hint', {
            format: dateInputFormatExample(item.value)
          })
        "
        v-on="on"
      />
    </template>
  </VSelect>
</template>
