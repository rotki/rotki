<template>
  <v-dialog v-if="value" :value="value" max-width="500" @input="input">
    <card>
      <template #title>{{ $t('date_format_help.title') }}</template>
      <template #subtitle>{{ $t('date_format_help.subtitle') }}</template>
      <template #buttons>
        <v-spacer />
        <v-btn depressed color="primary" @click="input(false)">
          {{ $t('date_format_help.close') }}
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
                $t('date_format_help.example', {
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

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import { displayDateFormatter } from '@/data/date_formatter';
import i18n from '@/i18n';

export default defineComponent({
  name: 'DateFormatHelp',
  props: {
    value: { required: true, type: Boolean }
  },
  emits: ['input'],
  setup(_, { emit }) {
    const input = (_value: boolean) => emit('input', _value);

    const formatter = displayDateFormatter;
    const directives: string[] = displayDateFormatter.directives;
    const now: Date = new Date('2018-03-09T21:09:08');

    const description = (directive: string): string => {
      const descriptions: { [directive: string]: string } = {
        a: i18n.t('date_format_help.directive.week_day_short').toString(),
        A: i18n.t('date_format_help.directive.week_day').toString(),
        w: i18n.t('date_format_help.directive.day_of_the_week').toString(),
        y: i18n.t('date_format_help.directive.year_two_digit').toString(),
        Y: i18n.t('date_format_help.directive.year').toString(),
        b: i18n.t('date_format_help.directive.month_short').toString(),
        B: i18n.t('date_format_help.directive.month').toString(),
        m: i18n.t('date_format_help.directive.month_two_digit').toString(),
        '-m': i18n.t('date_format_help.directive.month_numeric').toString(),
        d: i18n.t('date_format_help.directive.day_two_digit').toString(),
        '-d': i18n.t('date_format_help.directive.day_numeric').toString(),
        H: i18n.t('date_format_help.directive.hour_padded').toString(),
        '-H': i18n.t('date_format_help.directive.hour').toString(),
        I: i18n.t('date_format_help.directive.hour_twelve_padded').toString(),
        '-I': i18n.t('date_format_help.directive.hour_twelve').toString(),
        M: i18n.t('date_format_help.directive.minutes_padded').toString(),
        '-M': i18n.t('date_format_help.directive.minutes').toString(),
        S: i18n.t('date_format_help.directive.seconds_padded').toString(),
        '-S': i18n.t('date_format_help.directive.seconds').toString(),
        p: i18n.t('date_format_help.directive.ampm').toString(),
        z: i18n.t('date_format_help.directive.timezone_offset').toString(),
        Z: i18n.t('date_format_help.directive.timezone').toString(),
        j: i18n.t('date_format_help.directive.day_of_year_padded').toString(),
        '-j': i18n.t('date_format_help.directive.day_of_year').toString(),
        c: i18n.t('date_format_help.directive.locale_datetime').toString(),
        x: i18n.t('date_format_help.directive.locale_date').toString(),
        X: i18n.t('date_format_help.directive.locale_time').toString()
      };

      return descriptions[directive.replace('%', '')] ?? '';
    };

    return {
      directives,
      formatter,
      now,
      description,
      input
    };
  }
});
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
