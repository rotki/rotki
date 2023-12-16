<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean;
  count: number;
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: boolean): void;
}>();

const { t } = useI18n();

const model = useSimpleVModel(props, emit);
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
