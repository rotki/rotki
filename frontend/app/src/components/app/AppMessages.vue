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
      v-if="startupError.length > 0"
      :message="startupError"
      fatal
    />
    <mac-os-version-unsupported v-if="macosUnsupported" />
    <win-version-unsupported v-if="winUnsupported" />
  </fragment>
</template>

<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { useMessageStore } from '@/store/message';

const StartupErrorScreen = defineAsyncComponent(
  () => import('@/components/error/StartupErrorScreen.vue')
);
const MessageDialog = defineAsyncComponent(
  () => import('@/components/dialogs/MessageDialog.vue')
);
const MacOsVersionUnsupported = defineAsyncComponent(
  () => import('@/components/error/MacOsVersionUnsupported.vue')
);
const WinVersionUnsupported = defineAsyncComponent(
  () => import('@/components/error/WinVersionUnsupported.vue')
);

defineProps({
  startupError: { required: true, type: String },
  macosUnsupported: { required: true, type: Boolean },
  winUnsupported: { required: true, type: Boolean }
});

const store = useMessageStore();
const { message } = toRefs(store);
const { setMessage } = store;
const dismissMessage = () => setMessage();
</script>
