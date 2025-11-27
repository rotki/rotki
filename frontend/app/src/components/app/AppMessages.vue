<script setup lang="ts">
import PasswordConfirmationDialog from '@/components/account-management/login/PasswordConfirmationDialog.vue';
import AddressBookFormDialog from '@/components/address-book-manager/AddressBookFormDialog.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import MacOsVersionUnsupported from '@/components/error/MacOsVersionUnsupported.vue';
import StartupErrorScreen from '@/components/error/StartupErrorScreen.vue';
import WinVersionUnsupported from '@/components/error/WinVersionUnsupported.vue';
import { useAddressBookForm } from '@/composables/address-book/form';
import { useAutoLogin } from '@/composables/user/account';
import { useBackendMessagesStore } from '@/store/backend-messages';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';

defineSlots<{
  default: () => any;
}>();

const { isMacOsVersionUnsupported, isWinVersionUnsupported, startupErrorMessage }
  = storeToRefs(useBackendMessagesStore());
const store = useMessageStore();
const { message } = storeToRefs(store);
const { setMessage } = store;
const dismissMessage = () => setMessage();

const confirmStore = useConfirmStore();
const { confirm, dismiss } = confirmStore;
const { confirmation, visible } = storeToRefs(confirmStore);

const { globalPayload, openDialog } = useAddressBookForm();

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
</template>
