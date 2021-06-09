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
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { displayDateFormatter } from '@/data/date_formatter';

@Component({
  name: 'DateFormatHelp'
})
export default class DateFormatHelp extends Vue {
  @Prop({ required: true, type: Boolean })
  value!: boolean;

  @Emit()
  input(_value: boolean) {}

  readonly formatter = displayDateFormatter;
  readonly directives: string[] = displayDateFormatter.directives;
  readonly now: Date = new Date('2018-03-09T21:09:08');

  description(directive: string): string {
    const descriptions: { [directive: string]: string } = {
      a: this.$t('date_format_help.directive.week_day_short').toString(),
      A: this.$t('date_format_help.directive.week_day').toString(),
      w: this.$t('date_format_help.directive.day_of_the_week').toString(),
      y: this.$t('date_format_help.directive.year_two_digit').toString(),
      Y: this.$t('date_format_help.directive.year').toString(),
      b: this.$t('date_format_help.directive.month_short').toString(),
      B: this.$t('date_format_help.directive.month').toString(),
      m: this.$t('date_format_help.directive.month_two_digit').toString(),
      '-m': this.$t('date_format_help.directive.month_numeric').toString(),
      d: this.$t('date_format_help.directive.day_two_digit').toString(),
      '-d': this.$t('date_format_help.directive.day_numeric').toString(),
      H: this.$t('date_format_help.directive.hour_padded').toString(),
      '-H': this.$t('date_format_help.directive.hour').toString(),
      I: this.$t('date_format_help.directive.hour_twelve_padded').toString(),
      '-I': this.$t('date_format_help.directive.hour_twelve').toString(),
      M: this.$t('date_format_help.directive.minutes_padded').toString(),
      '-M': this.$t('date_format_help.directive.minutes').toString(),
      S: this.$t('date_format_help.directive.seconds_padded').toString(),
      '-S': this.$t('date_format_help.directive.seconds').toString(),
      p: this.$t('date_format_help.directive.ampm').toString(),
      z: this.$t('date_format_help.directive.timezone_offset').toString(),
      Z: this.$t('date_format_help.directive.timezone').toString(),
      j: this.$t('date_format_help.directive.day_of_year_padded').toString(),
      '-j': this.$t('date_format_help.directive.day_of_year').toString(),
      c: this.$t('date_format_help.directive.locale_datetime').toString(),
      x: this.$t('date_format_help.directive.locale_date').toString(),
      X: this.$t('date_format_help.directive.locale_time').toString()
    };

    return descriptions[directive.replace('%', '')] ?? '';
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.date-format-help {
  &__content {
    max-height: 300px;
    overflow-y: scroll;

    @extend .themed-scrollbar;
  }

  &__directive {
    width: 24px;
  }
}
</style>
