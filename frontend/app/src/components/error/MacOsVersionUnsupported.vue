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
import { Component, Vue } from 'vue-property-decorator';
import ErrorScreen from '@/components/error/ErrorScreen.vue';

@Component({
  components: { ErrorScreen }
})
export default class StartupErrorScreen extends Vue {
  terminate() {
    this.$interop.closeApp();
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.macos-unsupported {
  background-color: white;
}
</style>
