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
  <RuiMenuSelect
    v-bind="rootAttrs"
    :options="selections"
    :item-height="68"
    key-attr="value"
    text-attr="value"
    variant="outlined"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #item="{ item }">
      <ListItem
        no-hover
        no-padding
        class="!py-0"
        :title="item.value"
        :subtitle="
          t('general_settings.date_input_format_hint', {
            format: dateInputFormatExample(item.value),
          })
        "
      />
    </template>
  </RuiMenuSelect>
</template>
