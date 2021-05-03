<template>
  <div class="pa-4">
    <div class="text-h6">{{ $t('connection_failure.title') }}</div>
    <div class="text-body-1 mt-2 text--secondary">
      {{ $t('connection_failure.message') }}
    </div>
    <div class="full-width d-flex mt-2">
      <v-spacer />
      <v-btn depressed @click="terminate">
        {{ $t('connection_failure.terminate') }}
      </v-btn>
      <v-btn depressed color="primary" @click="retry">
        {{ $t('connection_failure.retry') }}
      </v-btn>
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class ConnectionFailure extends Vue {
  retry() {
    this.$store.dispatch('connect');
  }

  terminate() {
    this.$interop.closeApp();
  }
}
</script>
<style scoped lang="scss"></style>
