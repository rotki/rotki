<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

withDefaults(defineProps<{ full?: boolean }>(), { full: false });

const slots = useSlots();
</script>

<template>
  <FullSizeContent class="gap-4" :class="{ '!h-auto !mt-20': !full }">
    <div class="flex items-center justify-center">
      <div
        class="w-[8rem] h-[8rem] md:w-[16rem] md:h-[16rem] bg-rui-grey-200 p-8 md:p-16 rounded-full mb-8"
      >
        <slot name="logo">
          <RotkiLogo class="h-full w-full" :url="externalLinks.logo.noData" />
        </slot>
      </div>
    </div>
    <div v-if="slots.title" class="text-h5">
      <slot name="title" />
    </div>
    <div v-if="slots.default" class="text-subtitle-2 text--secondary">
      <slot />
    </div>
  </FullSizeContent>
</template>
