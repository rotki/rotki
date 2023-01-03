<script setup lang="ts">
import { type Blockchain } from '@rotki/common/lib/blockchain';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import AccountForm from '@/components/accounts/management/AccountForm.vue';

defineProps<{ context: Blockchain }>();

const { tc } = useI18n();

const { dialogText, openDialog, valid, clearDialog, save } = useAccountDialog();
const { loading } = useAccountLoading();
</script>

<template>
  <big-dialog
    :display="openDialog"
    :title="dialogText.title"
    :subtitle="dialogText.subtitle"
    :primary-action="tc('common.actions.save')"
    :secondary-action="tc('common.actions.cancel')"
    :action-disabled="!valid"
    :loading="loading"
    @confirm="save"
    @cancel="clearDialog()"
  >
    <account-form :context="context" data-cy="blockchain-balance-form" />
  </big-dialog>
</template>
