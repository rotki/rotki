<template>
  <error-screen
    class="macos-unsupported"
    :header="$t('macos_unsupported.header')"
    :alternative="$t('macos_unsupported.message')"
  >
    <v-btn
      depressed
      color="primary"
      @click="terminate()"
      v-text="$t('macos_unsupported.terminate')"
    />
  </error-screen>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import ErrorScreen from '@/components/error/ErrorScreen.vue';

import { interop } from '@/electron-interop';

export default defineComponent({
  name: 'StartupErrorScreen',
  components: { ErrorScreen },
  setup() {
    const terminate = () => {
      interop.closeApp();
    };

    return { terminate };
  }
});
</script>

<style scoped lang="scss">
.macos-unsupported {
  background-color: white;
}
</style>
