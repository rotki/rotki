<script setup lang="ts">
import ListItem from '@/components/common/ListItem.vue';
import { displayDateFormatter } from '@/data/date-formatter';
import { DateFormat } from '@/types/date-format';

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<string>({ required: true });

defineProps<{
  label: string;
  errorMessages: string[];
  successMessages: string[];
}>();

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
    v-bind="$attrs"
    v-model="modelValue"
    :label="label"
    :success-messages="successMessages"
    :error-messages="errorMessages"
    :options="selections"
    :item-height="68"
    key-attr="value"
    text-attr="value"
    variant="outlined"
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
