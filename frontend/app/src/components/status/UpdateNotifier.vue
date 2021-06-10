<template>
  <div v-if="updateAvailable">
    <v-snackbar v-model="updateAvailable" :timeout="-1" dark bottom right>
      {{ $t('update_notifier.update_available') }}
      <template #action>
        <v-btn text :loading="updating" @click="update">
          {{ $t('update_notifier.update') }}
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({
  name: 'UpdateNotifier'
})
export default class UpdateNotifier extends Vue {
  updating: boolean = false;
  updateAvailable: boolean = false;
  swRegistration: ServiceWorkerRegistration | null = null;

  created() {
    document.addEventListener('swUpdated', this.handleUpdate, { once: true });

    navigator.serviceWorker.addEventListener('controllerchange', () => {
      setTimeout(() => {
        this.updateAvailable = false;
        window.location.reload();
      }, 2000);
    });
  }

  beforeDestroy() {
    document.removeEventListener('swUpdated', this.handleUpdate);
  }

  handleUpdate(event: any) {
    this.swRegistration = event.detail;
    this.updateAvailable = true;
  }

  update() {
    this.updating = true;
    if (!this.swRegistration || !this.swRegistration.waiting) {
      return;
    }
    this.swRegistration.waiting.postMessage('skipWaiting');
  }
}
</script>

<style scoped lang="scss"></style>
