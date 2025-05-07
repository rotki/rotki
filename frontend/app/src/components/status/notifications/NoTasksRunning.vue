<script setup lang="ts">
import SuccessDisplay from '@/components/display/SuccessDisplay.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCard
    dense
    content-class="flex items-center gap-4"
  >
    <SuccessDisplay success />
    <div class="font-medium">
      {{ t('no_task_running.description') }}
    </div>
  </RuiCard>
</template>
