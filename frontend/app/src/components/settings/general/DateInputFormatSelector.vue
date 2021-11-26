<template>
  <v-select
    v-bind="$attrs"
    item-text="value"
    item-value="value"
    outlined
    persistent-hint
    :items="selections"
    v-on="$listeners"
  >
    <template #item="{ item, attrs, on }">
      <v-list-item v-bind="attrs" v-on="on">
        <v-list-item-content>
          <v-list-item-title>
            {{ item.value }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{
              $t('general_settings.date_input_format_hint', {
                format: dateInputFormatExample(item.value)
              })
            }}
          </v-list-item-subtitle>
        </v-list-item-content>
      </v-list-item>
    </template>
  </v-select>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { displayDateFormatter } from '@/data/date_formatter';
import { DateFormat } from '@/types/date-format';
export default defineComponent({
  name: 'DateFormatSelector',
  setup() {
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

    return {
      selections,
      dateInputFormatExample
    };
  }
});
</script>
