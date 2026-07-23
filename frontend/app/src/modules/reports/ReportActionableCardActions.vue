<script setup lang="ts">
const { isPinned, hint, step, totalSteps, isMissingAcquisitions } = defineProps<{
  isPinned: boolean;
  hint: string;
  step: number;
  totalSteps: number;
  isMissingAcquisitions: boolean;
}>();

const emit = defineEmits<{
  back: [];
  next: [];
  close: [];
  finish: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex items-center justify-between gap-4"
    :class="isPinned ? 'py-2' : 'p-4'"
  >
    <div
      v-if="hint"
      class="text-caption"
    >
      {{ hint }}
    </div>

    <div class="flex gap-2">
      <RuiButton
        v-if="step > 1"
        :size="isPinned ? 'sm' : undefined"
        variant="text"
        @click="emit('back')"
      >
        {{ t('common.actions.back') }}
      </RuiButton>
      <RuiButton
        v-if="step < totalSteps"
        color="primary"
        :size="isPinned ? 'sm' : undefined"
        @click="emit('next')"
      >
        {{ t('common.actions.next') }}
      </RuiButton>
      <template v-if="step === totalSteps">
        <RuiButton
          v-if="!isPinned && isMissingAcquisitions"
          color="primary"
          :size="isPinned ? 'sm' : undefined"
          @click="emit('close')"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
        <RuiButton
          v-else-if="!isMissingAcquisitions"
          color="primary"
          :size="isPinned ? 'sm' : undefined"
          @click="emit('finish')"
        >
          {{ t('common.actions.finish') }}
        </RuiButton>
      </template>
    </div>
  </div>
</template>
