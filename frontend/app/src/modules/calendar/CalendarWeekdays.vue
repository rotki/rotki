<script setup lang="ts">
import { getDayNames } from '@/modules/core/common/data/date';
import { useSetting } from '@/modules/settings/use-setting';

const language = useSetting('language');

const getDayNamesReactify = reactify(getDayNames);
const weekdays = getDayNamesReactify(language);
</script>

<template>
  <div
    v-for="weekday in weekdays"
    :key="weekday"
    class="border-b border-rui-divider bg-rui-surface-muted py-2 text-center text-[0.8125rem] leading-5 font-medium text-rui-text-secondary"
  >
    {{ weekday }}
  </div>
</template>
