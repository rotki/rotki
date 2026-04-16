<script setup lang="ts">
const model = defineModel<boolean>({ required: true });
defineProps<{
  count: number;
}>();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex justify-between items-center">
    <div class="flex items-center gap-4">
      <RuiProgress
        color="primary"
        variant="indeterminate"
        circular
        size="20"
        thickness="2"
      />
      <div class="font-medium">
        {{ t('collapsed_pending_tasks.title', { count }, count) }}
      </div>
    </div>

    <RuiButton
      class="-m-1"
      variant="text"
      icon
      size="sm"
      @click="model = !model"
    >
      <RuiIcon
        v-if="model"
        name="lu-chevron-up"
      />
      <RuiIcon
        v-else
        name="lu-chevron-down"
      />
    </RuiButton>
  </div>
</template>
