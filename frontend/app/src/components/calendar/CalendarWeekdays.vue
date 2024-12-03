<script setup lang="ts">
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { getDayNames } from '@/utils/date';

const { language } = storeToRefs(useFrontendSettingsStore());

const getDayNamesReactify = reactify(getDayNames);
const weekdays = getDayNamesReactify(language);
</script>

<template>
  <div
    v-for="weekday in weekdays"
    :key="weekday"
    class="text-center text-subtitle-2 text-sm uppercase font-medium text-rui-text-secondary pt-2 border-default"
  >
    {{ weekday }}
  </div>
</template>
