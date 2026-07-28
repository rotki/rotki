<script setup lang="ts">
import type { UnmatchedRowConfirm } from '@/modules/history/events/unmatched-actions';

const { confirm, loading = false } = defineProps<{
  confirm: UnmatchedRowConfirm;
  loading?: boolean;
}>();

const emit = defineEmits<{
  cancel: [];
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <!-- amber, not red: this is guidance about reversible work, not a destructive warning -->
  <div
    class="flex items-center gap-2 rounded px-2 py-1 bg-rui-warning/10 border border-rui-warning/40"
    data-testid="unmatched-confirm-strip"
  >
    <span class="flex-1 min-w-0 text-caption text-rui-text">
      {{ confirm.message }}
    </span>
    <RuiButton
      size="sm"
      variant="text"
      class="!h-[26px] !py-0 shrink-0"
      data-testid="unmatched-confirm-cancel"
      @click="emit('cancel')"
    >
      {{ t('common.actions.cancel') }}
    </RuiButton>
    <RuiButton
      size="sm"
      color="warning"
      class="!h-[26px] !py-0 shrink-0"
      :loading="loading"
      data-testid="unmatched-confirm-accept"
      @click="emit('confirm')"
    >
      {{ confirm.confirmLabel }}
    </RuiButton>
  </div>
</template>
