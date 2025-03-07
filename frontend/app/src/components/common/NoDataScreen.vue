<script setup lang="ts">
import FullSizeContent from '@/components/common/FullSizeContent.vue';
import RotkiLogo from '@/components/common/RotkiLogo.vue';

withDefaults(defineProps<{ full?: boolean }>(), { full: false });

const { isMdAndUp } = useBreakpoint();
</script>

<template>
  <FullSizeContent
    class="gap-4"
    :class="{ '!h-auto !mt-20': !full }"
  >
    <div class="flex items-center justify-center">
      <div
        class="bg-rui-grey-200 dark:bg-rui-grey-900 rounded-full mb-8"
        :class="[isMdAndUp ? 'w-64 h-64 p-16' : 'w-32 h-32 p-8']"
      >
        <slot name="logo">
          <RotkiLogo
            :size="isMdAndUp ? 8 : 4"
            logo="emptyScreen"
            unique-key="3"
          />
        </slot>
      </div>
    </div>
    <div
      v-if="$slots.title"
      class="text-h5"
    >
      <slot name="title" />
    </div>
    <div
      v-if="$slots.default"
      class="text-subtitle-2 text-rui-text-secondary"
    >
      <slot />
    </div>
  </FullSizeContent>
</template>
