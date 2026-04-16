<script setup lang="ts">
import AddressBookFormDialog from '@/modules/accounts/address-book/AddressBookFormDialog.vue';
import { useAddressBookForm } from '@/modules/accounts/address-book/use-address-book-form';
import PasswordConfirmationDialog from '@/modules/auth/login/PasswordConfirmationDialog.vue';
import { useAutoLogin } from '@/modules/auth/use-auto-login';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useReportIssue } from '@/modules/core/common/use-report-issue';
import { useBackendMessages } from '@/modules/shell/app/use-backend-messages';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';
import MessageDialog from '@/modules/shell/components/dialogs/MessageDialog.vue';
import MacOsVersionUnsupported from '@/modules/shell/components/error/MacOsVersionUnsupported.vue';
import StartupErrorScreen from '@/modules/shell/components/error/StartupErrorScreen.vue';
import WinVersionUnsupported from '@/modules/shell/components/error/WinVersionUnsupported.vue';
import ReportIssueDialog from '@/modules/shell/components/ReportIssueDialog.vue';

defineSlots<{
  default: () => any;
}>();

const { isMacOsVersionUnsupported, isWinVersionUnsupported, startupErrorMessage }
  = useBackendMessages();
const store = useMessageStore();
const { message } = storeToRefs(store);
const { setMessage } = store;
const dismissMessage = () => setMessage();

const confirmStore = useConfirmStore();
const { confirm, dismiss } = confirmStore;
const { confirmation, visible } = storeToRefs(confirmStore);

const { globalPayload, openDialog } = useAddressBookForm();

const { visible: reportIssueVisible } = useReportIssue();

const { confirmPassword, needsPasswordConfirmation, username } = useAutoLogin();

const { t } = useI18n({ useScope: 'global' });

const passwordError = ref<string>('');

whenever(needsPasswordConfirmation, () => {
  set(passwordError, ''); // Clear any previous error
});

async function handlePasswordConfirmation(password: string): Promise<void> {
  set(passwordError, ''); // Clear error before attempting
  const success = await confirmPassword(password);
  if (!success)
    set(passwordError, t('password_confirmation_dialog.validation.incorrect_password'));
}
</script>

<template>
  <slot />
  <AddressBookFormDialog
    v-model:open="openDialog"
    :editable-item="globalPayload"
    :edit-mode="false"
    root
  />
  <MessageDialog
    v-if="message"
    :message="message"
    @dismiss="dismissMessage()"
  />
  <ConfirmDialog
    v-if="visible"
    :display="visible"
    :title="confirmation.title"
    :message="confirmation.message"
    :single-action="confirmation.singleAction"
    :primary-action="confirmation.primaryAction"
    :confirm-type="confirmation.type || 'warning'"
    @confirm="confirm()"
    @cancel="dismiss()"
  />
  <PasswordConfirmationDialog
    v-if="needsPasswordConfirmation"
    v-model="needsPasswordConfirmation"
    :username="username"
    :error-message="passwordError"
    @confirm="handlePasswordConfirmation($event)"
  />
  <StartupErrorScreen
    v-if="startupErrorMessage.length > 0"
    :message="startupErrorMessage"
  />
  <MacOsVersionUnsupported v-if="isMacOsVersionUnsupported" />
  <WinVersionUnsupported v-if="isWinVersionUnsupported" />
  <ReportIssueDialog v-if="reportIssueVisible" />
</template>
