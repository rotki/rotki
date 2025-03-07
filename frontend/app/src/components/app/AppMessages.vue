<script setup lang="ts">
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useBackendMessagesStore } from '@/store/backend-messages';
import { useAddressBookForm } from '@/composables/address-book/form';
import WinVersionUnsupported from '@/components/error/WinVersionUnsupported.vue';
import MacOsVersionUnsupported from '@/components/error/MacOsVersionUnsupported.vue';
import StartupErrorScreen from '@/components/error/StartupErrorScreen.vue';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import AddressBookFormDialog from '@/components/address-book-manager/AddressBookFormDialog.vue';

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
  <StartupErrorScreen
    v-if="startupErrorMessage.length > 0"
    :message="startupErrorMessage"
  />
  <MacOsVersionUnsupported v-if="isMacOsVersionUnsupported" />
  <WinVersionUnsupported v-if="isWinVersionUnsupported" />
</template>
