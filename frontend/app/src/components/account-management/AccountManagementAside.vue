<script lang="ts" setup>
import SponsorshipView from '@/components/sponsorship/SponsorshipView.vue';

defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <div class="max-w-[31rem] mx-auto lg:max-w-[29%] flex-col grow-0 lg:flex-1 border-b lg:border-b-0 border-default lg:border-l h-full relative overflow-auto hidden lg:flex justify-between">
    <div class="p-6 lg:px-8 lg:py-12 xl:p-12 flex-1 overflow-auto">
      <slot />
    </div>

    <SponsorshipView class="border-t border-default bottom-0 right-0 px-6 py-3" />
  </div>
</template>
