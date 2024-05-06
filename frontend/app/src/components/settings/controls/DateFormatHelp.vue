<script setup lang="ts">
import { displayDateFormatter } from '@/data/date-formatter';

const props = defineProps<{ value: boolean }>();

const emit = defineEmits<{ (e: 'input', value: boolean): void }>();

const display = useSimpleVModel(props, emit);

const formatter = displayDateFormatter;
const directives: string[] = displayDateFormatter.directives;
const now: Date = new Date('2018-03-09T21:09:08');

const { t } = useI18n();

function description(directive: string): string {
  const descriptions: Record<string, string> = {
    'a': t('date_format_help.directive.week_day_short').toString(),
    'A': t('date_format_help.directive.week_day').toString(),
    'w': t('date_format_help.directive.day_of_the_week').toString(),
    'y': t('date_format_help.directive.year_two_digit').toString(),
    'Y': t('date_format_help.directive.year').toString(),
    'b': t('date_format_help.directive.month_short').toString(),
    'B': t('date_format_help.directive.month').toString(),
    'm': t('date_format_help.directive.month_two_digit').toString(),
    '-m': t('date_format_help.directive.month_numeric').toString(),
    'd': t('date_format_help.directive.day_two_digit').toString(),
    '-d': t('date_format_help.directive.day_numeric').toString(),
    'H': t('date_format_help.directive.hour_padded').toString(),
    '-H': t('date_format_help.directive.hour').toString(),
    'I': t('date_format_help.directive.hour_twelve_padded').toString(),
    '-I': t('date_format_help.directive.hour_twelve').toString(),
    'M': t('date_format_help.directive.minutes_padded').toString(),
    '-M': t('date_format_help.directive.minutes').toString(),
    'S': t('date_format_help.directive.seconds_padded').toString(),
    '-S': t('date_format_help.directive.seconds').toString(),
    's': t('date_format_help.directive.milliseconds').toString(),
    'p': t('date_format_help.directive.ampm').toString(),
    'z': t('date_format_help.directive.timezone_offset').toString(),
    'Z': t('date_format_help.directive.timezone').toString(),
    'j': t('date_format_help.directive.day_of_year_padded').toString(),
    '-j': t('date_format_help.directive.day_of_year').toString(),
    'c': t('date_format_help.directive.locale_datetime').toString(),
    'x': t('date_format_help.directive.locale_date').toString(),
    'X': t('date_format_help.directive.locale_time').toString(),
  };

  return descriptions[directive.replace('%', '')] ?? '';
}
</script>

<template>
  <RuiDialog
    v-model="display"
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
          @click="display = false"
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
