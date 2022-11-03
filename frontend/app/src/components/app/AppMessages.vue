<template>
  <fragment>
    <slot />
    <message-dialog
      :title="message.title"
      :message="message.description"
      :success="message.success"
      @dismiss="dismissMessage()"
    />
    <startup-error-screen
      v-if="startupErrorMessage.length > 0"
      :message="startupErrorMessage"
      fatal
    />
    <mac-os-version-unsupported v-if="isMacOsVersionUnsupported" />
    <win-version-unsupported v-if="isWinVersionUnsupported" />
  </fragment>
</template>

<script setup lang="ts">
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import MacOsVersionUnsupported from '@/components/error/MacOsVersionUnsupported.vue';
import StartupErrorScreen from '@/components/error/StartupErrorScreen.vue';
import WinVersionUnsupported from '@/components/error/WinVersionUnsupported.vue';
import Fragment from '@/components/helper/Fragment';
import { useBackendMessagesStore } from '@/store/backend-messages';
import { useMessageStore } from '@/store/message';

const {
  startupErrorMessage,
  isMacOsVersionUnsupported,
  isWinVersionUnsupported
} = storeToRefs(useBackendMessagesStore());
const store = useMessageStore();
const { message } = storeToRefs(store);
const { setMessage } = store;
const dismissMessage = () => setMessage();
</script>
