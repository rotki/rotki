<script setup lang="ts">
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
</script>

<template>
  <div>
    <SettingCategoryHeader class="border-b pb-5">
      <template #title>
        <slot name="title" />
      </template>
      <template
        v-if="$slots.subtitle"
        #subtitle
      >
        <slot name="subtitle" />
      </template>
    </SettingCategoryHeader>
    <slot />
  </div>
</template>
