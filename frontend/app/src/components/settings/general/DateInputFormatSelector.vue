<script setup lang="ts">
import { useListeners } from 'vue';
import { displayDateFormatter } from '@/data/date_formatter';
import { DateFormat } from '@/types/date-format';

const rootAttrs = useAttrs();
const rootListeners = useListeners();

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
    v-on="rootListeners"
  >
    <template #item="{ item, attrs, on }">
      <VListItem v-bind="attrs" v-on="on">
        <VListItemContent>
          <VListItemTitle>
            {{ item.value }}
          </VListItemTitle>
          <VListItemSubtitle>
            {{
              t('general_settings.date_input_format_hint', {
                format: dateInputFormatExample(item.value)
              })
            }}
          </VListItemSubtitle>
        </VListItemContent>
      </VListItem>
    </template>
  </VSelect>
</template>
