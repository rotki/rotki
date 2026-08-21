<script setup lang="ts">
const { message, loading = false } = defineProps<{
  message: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  dismiss: [];
  undo: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <!-- info, not amber: the confirm strip asks before reversible work, this one reports work
       that already happened and keeps its undo within reach of the list it changed -->
  <div
    class="flex items-center gap-2 rounded px-2 py-1 bg-rui-info/10 border border-rui-info/40"
    data-testid="unmatched-resolution-strip"
  >
    <span class="flex-1 min-w-0 text-caption text-rui-text">
      {{ message }}
    </span>
    <RuiButton
      size="sm"
      variant="text"
      class="!h-[26px] !py-0 shrink-0"
      :loading="loading"
      data-testid="unmatched-resolution-undo"
      @click="emit('undo')"
    >
      {{ t('common.actions.undo') }}
    </RuiButton>
    <RuiButton
      size="sm"
      variant="text"
      icon
      class="!h-[26px] !w-[26px] shrink-0"
      :aria-label="t('common.actions.dismiss')"
      data-testid="unmatched-resolution-dismiss"
      @click="emit('dismiss')"
    >
      <RuiIcon
        name="lu-x"
        size="16"
      />
    </RuiButton>
  </div>
</template>
