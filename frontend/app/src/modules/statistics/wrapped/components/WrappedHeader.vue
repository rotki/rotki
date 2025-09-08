<script setup lang="ts">
import RotkiLogo from '@/components/common/RotkiLogo.vue';

defineProps<{
  highlightedYear?: number;
  isHighlightedYear: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="py-8 w-full rounded-lg flex flex-col items-center bg-gradient-to-b from-transparent to-rui-primary/[0.05]">
    <RotkiLogo
      :size="3"
      class="mb-4"
    />
    <h2 class="text-4xl font-bold mb-2">
      {{ t('wrapped.title', { year: isHighlightedYear && highlightedYear ? `${highlightedYear}` : undefined }) }}
    </h2>
    <p class="text-xl text-rui-text-secondary">
      {{ t('wrapped.year_subtitle') }}
    </p>
  </div>
</template>
