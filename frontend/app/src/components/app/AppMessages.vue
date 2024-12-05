<script setup lang="ts">
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useBackendMessagesStore } from '@/store/backend-messages';
import { useAddressBookForm } from '@/composables/address-book/form';

const { isMacOsVersionUnsupported, isWinVersionUnsupported, startupErrorMessage }
  = storeToRefs(useBackendMessagesStore());
const store = useMessageStore();
const { message } = storeToRefs(store);
const { setMessage } = store;
const dismissMessage = () => setMessage();

const confirmStore = useConfirmStore();
const { confirm, dismiss } = confirmStore;
const { confirmation, visible } = storeToRefs(confirmStore);

const { globalPayload } = useAddressBookForm();
</script>

<template>
  <slot />
  <AddressBookFormDialog
    :payload="globalPayload"
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
