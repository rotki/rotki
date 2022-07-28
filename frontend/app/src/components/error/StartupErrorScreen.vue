<template>
  <error-screen
    class="start-error-screen"
    :header="$t('error_screen.start_failure')"
    :title="$t('error_screen.backend_error')"
    :subtitle="$t('error_screen.message')"
    :message="message"
  >
    <div class="d-flex mb-4">
      <v-btn
        depressed
        color="primary"
        @click="terminate()"
        v-text="$t('error_screen.terminate')"
      />
      <v-btn
        text
        color="primary"
        class="ml-4"
        @click="reset"
        v-text="$t('error_screen.reset_backend_setting')"
      />
    </div>
  </error-screen>
</template>

<script lang="ts">
import { defineComponent, toRefs } from '@vue/composition-api';
import { useClipboard } from '@vueuse/core';
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import BackendSettings from '@/components/settings/BackendSettings.vue';
import { saveUserOptions } from '@/composables/backend';
import { interop } from '@/electron-interop';
import { useMainStore } from '@/store/store';

export default defineComponent({
  name: 'StartupErrorScreen',
  components: { ErrorScreen },
  mixins: [BackendSettings],
  props: {
    message: { required: true, type: String }
  },
  setup(props) {
    const { message } = toRefs(props);

    const terminate = () => {
      interop.closeApp();
    };

    const { setConnected, connect } = useMainStore();

    const reset = async () => {
      saveUserOptions({});
      await setConnected(false);
      const fileConfig = await interop.config(false);
      await interop.restartBackend({ ...fileConfig });
      await connect();
    };

    const { copy: copyText } = useClipboard({ source: message });

    const copy = () => copyText();

    return {
      terminate,
      reset,
      copy
    };
  }
});
</script>

<style scoped lang="scss">
.startup-error-screen {
  background-color: white;
}
</style>
