<script setup lang="ts">
const { startupErrorMessage, isMacOsVersionUnsupported, isWinVersionUnsupported }
  = storeToRefs(useBackendMessagesStore());
const store = useMessageStore();
const { message } = storeToRefs(store);
const { setMessage } = store;
const dismissMessage = () => setMessage();

const confirmStore = useConfirmStore();
const { dismiss, confirm } = confirmStore;
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
    :title="message.title"
    :message="message.description"
    :success="message.success"
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
