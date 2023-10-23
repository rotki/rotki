<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';

defineProps<{ context: Blockchain }>();

const { t } = useI18n();

const {
  dialogText,
  openDialog,
  clearDialog,
  trySubmit,
  setPostSubmitFunc,
  submitting
} = useAccountDialog();
const { loading } = useAccountLoading();

const postSubmitFunc = (result: boolean) => {
  if (result) {
    clearDialog();
  }
};

setPostSubmitFunc(postSubmitFunc);
</script>

<template>
  <BigDialog
    :display="openDialog"
    :title="dialogText.title"
    :subtitle="dialogText.subtitle"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="loading || submitting"
    @confirm="trySubmit()"
    @cancel="clearDialog()"
  >
    <AccountForm :context="context" data-cy="blockchain-balance-form" />
  </BigDialog>
</template>
