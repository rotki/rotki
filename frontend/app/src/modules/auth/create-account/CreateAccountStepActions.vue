<script setup lang="ts">
const {
  issueCount = 0,
  loading = false,
  nextLabel,
  nextTestId,
} = defineProps<{
  nextLabel: string;
  nextTestId: string;
  loading?: boolean;
  /** Fields still showing an error after a Continue, 0 for none. */
  issueCount?: number;
}>();

const emit = defineEmits<{
  back: [];
  next: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col gap-2">
    <p
      v-if="issueCount > 0"
      role="status"
      class="text-caption text-rui-error"
      data-testid="create-account-issue-count"
    >
      {{ t('create_account.issue_count', { count: issueCount }, issueCount) }}
    </p>
    <div class="grid grid-cols-[1fr_2fr] gap-3">
      <RuiButton
        size="lg"
        class="w-full"
        type="button"
        data-testid="create-account-back"
        :disabled="loading"
        @click="emit('back')"
      >
        {{ t('common.actions.back') }}
      </RuiButton>
      <RuiButton
        size="lg"
        class="w-full"
        color="primary"
        type="button"
        :data-testid="nextTestId"
        :loading="loading"
        :disabled="loading"
        @click="emit('next')"
      >
        {{ nextLabel }}
      </RuiButton>
    </div>
  </div>
</template>
