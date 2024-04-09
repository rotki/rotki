<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
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
