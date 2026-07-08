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
    class="text-center text-subtitle-2 text-sm uppercase font-medium text-rui-text-secondary pt-2 border-default"
  >
    {{ weekday }}
  </div>
</template>
