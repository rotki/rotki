<template>
  <v-dialog v-if="value" :value="value" max-width="500" @input="input">
    <card>
      <template #title>{{ t('date_format_help.title') }}</template>
      <template #subtitle>{{ t('date_format_help.subtitle') }}</template>
      <template #buttons>
        <v-spacer />
        <v-btn depressed color="primary" @click="input(false)">
          {{ t('common.actions.close') }}
        </v-btn>
      </template>
      <div class="date-format-help__content">
        <div v-for="directive in directives" :key="directive" class="mt-2">
          <div>
            <span class="font-weight-medium date-format-help__directive">
              {{ directive }}
            </span>
            <span class="text--secondary ml-2">
              {{ description(directive) }}
            </span>
          </div>
          <div>
            <span class="ms-8">
              {{
                t('date_format_help.example', {
                  example: formatter.format(now, directive)
                })
              }}
            </span>
          </div>
        </div>
      </div>
    </card>
  </v-dialog>
</template>

<script setup lang="ts">
import { displayDateFormatter } from '@/data/date_formatter';

defineProps({
  value: { required: true, type: Boolean }
});

const emit = defineEmits(['input']);
const input = (_value: boolean) => emit('input', _value);

const formatter = displayDateFormatter;
const directives: string[] = displayDateFormatter.directives;
const now: Date = new Date('2018-03-09T21:09:08');

const { t } = useI18n();

const description = (directive: string): string => {
  const descriptions: { [directive: string]: string } = {
    a: t('date_format_help.directive.week_day_short').toString(),
    A: t('date_format_help.directive.week_day').toString(),
    w: t('date_format_help.directive.day_of_the_week').toString(),
    y: t('date_format_help.directive.year_two_digit').toString(),
    Y: t('date_format_help.directive.year').toString(),
    b: t('date_format_help.directive.month_short').toString(),
    B: t('date_format_help.directive.month').toString(),
    m: t('date_format_help.directive.month_two_digit').toString(),
    '-m': t('date_format_help.directive.month_numeric').toString(),
    d: t('date_format_help.directive.day_two_digit').toString(),
    '-d': t('date_format_help.directive.day_numeric').toString(),
    H: t('date_format_help.directive.hour_padded').toString(),
    '-H': t('date_format_help.directive.hour').toString(),
    I: t('date_format_help.directive.hour_twelve_padded').toString(),
    '-I': t('date_format_help.directive.hour_twelve').toString(),
    M: t('date_format_help.directive.minutes_padded').toString(),
    '-M': t('date_format_help.directive.minutes').toString(),
    S: t('date_format_help.directive.seconds_padded').toString(),
    '-S': t('date_format_help.directive.seconds').toString(),
    p: t('date_format_help.directive.ampm').toString(),
    z: t('date_format_help.directive.timezone_offset').toString(),
    Z: t('date_format_help.directive.timezone').toString(),
    j: t('date_format_help.directive.day_of_year_padded').toString(),
    '-j': t('date_format_help.directive.day_of_year').toString(),
    c: t('date_format_help.directive.locale_datetime').toString(),
    x: t('date_format_help.directive.locale_date').toString(),
    X: t('date_format_help.directive.locale_time').toString()
  };

  return descriptions[directive.replace('%', '')] ?? '';
};
</script>

<style scoped lang="scss">
.date-format-help {
  &__content {
    max-height: 300px;
    overflow-y: scroll;
  }

  &__directive {
    width: 24px;
  }
}
</style>
