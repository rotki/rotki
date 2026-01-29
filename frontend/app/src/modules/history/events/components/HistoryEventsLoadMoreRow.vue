<script setup lang="ts">
defineProps<{
  hiddenCount: number;
  totalCount: number;
}>();

const emit = defineEmits<{
  'load-more': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="h-9 flex items-center justify-center border-b border-default">
    <RuiButton
      variant="text"
      color="primary"
      size="sm"
      @click="emit('load-more')"
    >
      {{ t('transactions.events.view.load_more', { length: hiddenCount }) }}
      <template #append>
        <RuiIcon
          name="lu-chevron-down"
          size="16"
        />
      </template>
    </RuiButton>
  </div>
</template>
