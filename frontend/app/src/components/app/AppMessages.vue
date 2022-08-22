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
  </fragment>
</template>

<script lang="ts">
import { defineAsyncComponent, defineComponent, toRefs } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { useMainStore } from '@/store/main';

export default defineComponent({
  name: 'AppMessages',
  components: {
    Fragment,
    StartupErrorScreen: defineAsyncComponent(
      () => import('@/components/error/StartupErrorScreen.vue')
    ),

    MessageDialog: defineAsyncComponent(
      () => import('@/components/dialogs/MessageDialog.vue')
    ),
    MacOsVersionUnsupported: defineAsyncComponent(
      () => import('@/components/error/MacOsVersionUnsupported.vue')
    )
  },
  props: {
    startupError: { required: true, type: String },
    macosUnsupported: { required: true, type: Boolean }
  },
  setup() {
    const store = useMainStore();
    const { message } = toRefs(store);
    const { setMessage } = store;
    const dismissMessage = () => setMessage();
    return {
      message,
      dismissMessage
    };
  }
});
</script>
