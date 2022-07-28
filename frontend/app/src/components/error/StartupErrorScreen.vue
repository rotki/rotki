<template>
  <error-screen
    class="start-error-screen"
    :header="$t('error_screen.start_failure')"
    :title="$t('error_screen.backend_error')"
    :subtitle="$t('error_screen.message')"
    :message="message"
  >
    <v-btn
      depressed
      color="primary"
      @click="terminate()"
      v-text="$t('error_screen.terminate')"
    />
  </error-screen>
</template>

<script lang="ts">
import { defineComponent, toRefs } from '@vue/composition-api';
import { useClipboard } from '@vueuse/core';
import ErrorScreen from '@/components/error/ErrorScreen.vue';

import { interop } from '@/electron-interop';

export default defineComponent({
  name: 'StartupErrorScreen',
  components: { ErrorScreen },
  props: {
    message: { required: true, type: String }
  },
  setup(props) {
    const { message } = toRefs(props);

    const terminate = () => {
      interop.closeApp();
    };

    const { copy: copyText } = useClipboard({ source: message });

    const copy = () => copyText();

    return {
      terminate,
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
