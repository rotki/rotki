<script setup lang="ts">
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const open = defineModel<boolean>({ required: true });

const { loading = false, failure } = defineProps<{
  loading?: boolean;
  /** Why the last resolve failed; the dialog stays open, its Resolve button being the retry. */
  failure?: unknown;
}>();

const emit = defineEmits<{
  confirm: [note: string | undefined];
}>();

const { t } = useI18n({ useScope: 'global' });

const note = ref<string>('');

watch(open, (isOpen) => {
  if (isOpen)
    set(note, '');
});

function confirm(): void {
  const trimmed = get(note).trim();
  emit('confirm', trimmed.length > 0 ? trimmed : undefined);
}
</script>

<template>
  <RuiDialog
    v-model="open"
    max-width="500"
  >
    <RuiCard data-testid="data-issue-resolve-dialog">
      <template #header>
        {{ t('data_issues.resolve_dialog.title') }}
      </template>

      <RuiAlert
        type="info"
        class="mb-4"
      >
        {{ t('data_issues.resolve_dialog.notice') }}
      </RuiAlert>

      <FailureStrip
        v-if="failure"
        class="mb-4"
        :title="t('data_issues.action.resolve.error')"
        :failure="failure"
        data-testid="data-issue-resolve-failure"
      />

      <RuiTextArea
        v-model="note"
        color="primary"
        :label="t('data_issues.resolve_dialog.note_label')"
        :hint="t('data_issues.resolve_dialog.note_hint')"
        :rows="3"
        data-testid="data-issue-resolve-note"
      />

      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          @click="open = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :loading="loading"
          data-testid="data-issue-resolve-confirm"
          @click="confirm()"
        >
          {{ t('data_issues.resolve_dialog.confirm') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
