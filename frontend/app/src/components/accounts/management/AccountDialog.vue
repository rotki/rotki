<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

defineProps<{ context: Blockchain }>();

const { t } = useI18n();

const { dialogText, openDialog, valid, clearDialog, save } = useAccountDialog();
const { loading } = useAccountLoading();
</script>

<template>
  <big-dialog
    :display="openDialog"
    :title="dialogText.title"
    :subtitle="dialogText.subtitle"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :action-disabled="!valid || loading"
    :loading="loading"
    @confirm="save()"
    @cancel="clearDialog()"
  >
    <account-form :context="context" data-cy="blockchain-balance-form" />
  </big-dialog>
</template>
