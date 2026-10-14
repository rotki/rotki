<script setup lang="ts">
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';

defineSlots<{
  title?: () => any;
  subtitle?: () => any;
  default: () => any;
}>();
</script>

<template>
  <div>
    <SettingCategoryHeader
      v-if="$slots.title"
      class="border-b pb-4"
    >
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
