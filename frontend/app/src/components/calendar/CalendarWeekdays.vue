<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

function getWeekdays(locale = 'en') {
  const format = new Intl.DateTimeFormat(locale, { weekday: 'short' });
  const days = [];
  for (let day = 1; day <= 7; day++) {
    const date = new Date(Date.UTC(2022, 0, day + 2)); // +2 because 2022-01-02 is a Sunday
    days.push(format.format(date));
  }
  return days;
}

const { language } = storeToRefs(useFrontendSettingsStore());

const weekdays = computed(() => getWeekdays(get(language)));
</script>

<template>
  <Fragment>
    <div
      v-for="weekday in weekdays"
      :key="weekday"
      class="text-center text-subtitle-2 text-sm uppercase font-medium text-rui-text-secondary pt-2 border-default"
    >
      {{ weekday }}
    </div>
  </fragment>
</template>
