<script setup lang="ts">
defineProps<{
  count: number;
}>();
const model = defineModel<boolean>({ required: true });

const { t } = useI18n();
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
        name="arrow-up-s-line"
      />
      <RuiIcon
        v-else
        name="arrow-down-s-line"
      />
    </RuiButton>
  </div>
</template>
