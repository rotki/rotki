<script setup lang="ts">
import { displayDateFormatter } from '@/data/date-formatter';

const model = defineModel<boolean>({ required: true });

const formatter = displayDateFormatter;
const directives: string[] = displayDateFormatter.directives;
const now: Date = new Date('2018-03-09T21:09:08');

const { t } = useI18n();

function description(directive: string): string {
  const descriptions: Record<string, string> = {
    'a': t('date_format_help.directive.week_day_short'),
    'A': t('date_format_help.directive.week_day'),
    'w': t('date_format_help.directive.day_of_the_week'),
    'y': t('date_format_help.directive.year_two_digit'),
    'Y': t('date_format_help.directive.year'),
    'b': t('date_format_help.directive.month_short'),
    'B': t('date_format_help.directive.month'),
    'm': t('date_format_help.directive.month_two_digit'),
    '-m': t('date_format_help.directive.month_numeric'),
    'd': t('date_format_help.directive.day_two_digit'),
    '-d': t('date_format_help.directive.day_numeric'),
    'H': t('date_format_help.directive.hour_padded'),
    '-H': t('date_format_help.directive.hour'),
    'I': t('date_format_help.directive.hour_twelve_padded'),
    '-I': t('date_format_help.directive.hour_twelve'),
    'M': t('date_format_help.directive.minutes_padded'),
    '-M': t('date_format_help.directive.minutes'),
    'S': t('date_format_help.directive.seconds_padded'),
    '-S': t('date_format_help.directive.seconds'),
    's': t('date_format_help.directive.milliseconds'),
    'p': t('date_format_help.directive.ampm'),
    'z': t('date_format_help.directive.timezone_offset'),
    'Z': t('date_format_help.directive.timezone'),
    'j': t('date_format_help.directive.day_of_year_padded'),
    '-j': t('date_format_help.directive.day_of_year'),
    'c': t('date_format_help.directive.locale_datetime'),
    'x': t('date_format_help.directive.locale_date'),
    'X': t('date_format_help.directive.locale_time'),
  };

  return descriptions[directive.replace('%', '')] ?? '';
}
</script>

<template>
  <RuiDialog
    v-model="model"
    max-width="500"
  >
    <RuiCard>
      <template #header>
        {{ t('date_format_help.title') }}
      </template>
      <template #subheader>
        {{ t('date_format_help.subtitle') }}
      </template>
      <div class="date-format-help__content flex flex-col gap-2">
        <div
          v-for="directive in directives"
          :key="directive"
        >
          <div class="flex gap-2">
            <span class="w-8 font-medium">
              {{ directive }}
            </span>
            <span class="text-rui-text-secondary">
              {{ description(directive) }}
            </span>
          </div>
          <div class="ml-10">
            {{
              t('date_format_help.example', {
                example: formatter.format(now, directive),
              })
            }}
          </div>
        </div>
      </div>

      <template #footer>
        <div class="grow" />
        <RuiButton
          color="primary"
          @click="model = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>

<style scoped lang="scss">
.date-format-help {
  &__content {
    max-height: 300px;
    overflow-y: scroll;
  }
}
</style>
