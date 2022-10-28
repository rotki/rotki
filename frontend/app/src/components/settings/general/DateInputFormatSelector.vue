<template>
  <v-select
    v-bind="rootAttrs"
    item-text="value"
    item-value="value"
    outlined
    persistent-hint
    :items="selections"
    v-on="rootListeners"
  >
    <template #item="{ item, attrs, on }">
      <v-list-item v-bind="attrs" v-on="on">
        <v-list-item-content>
          <v-list-item-title>
            {{ item.value }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{
              t('general_settings.date_input_format_hint', {
                format: dateInputFormatExample(item.value)
              })
            }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
    </template>
  </v-select>
</template>

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

const dateInputFormatExample = (format: DateFormat): string => {
  return displayDateFormatter.format(new Date(), format);
};

const { t } = useI18n();
</script>
