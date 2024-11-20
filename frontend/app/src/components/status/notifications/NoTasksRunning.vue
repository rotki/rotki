<script setup lang="ts">
const { t } = useI18n();
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
