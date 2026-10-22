<script setup lang="ts">
import { RestoreOutcomeKind, useRestoreOutcomeNotice } from '@/modules/session/use-restore-outcome-notice';

const { t } = useI18n({ useScope: 'global' });

const { dismiss, outcome } = useRestoreOutcomeNotice();

const restored = computed<boolean>(() => get(outcome)?.kind === RestoreOutcomeKind.RESTORED);
</script>

<template>
  <RuiAlert
    v-if="outcome"
    :type="restored ? 'success' : 'error'"
    :title="restored ? t('actions.session.force_sync.success.title') : t('actions.session.force_sync.error.title')"
    class="mb-6"
    closeable
    data-testid="restore-outcome-notice"
    @close="dismiss()"
  >
    {{ outcome.message }}
  </RuiAlert>
</template>
