<template>
  <div v-if="needRefresh">
    <v-snackbar v-model="needRefresh" :timeout="-1" dark bottom right>
      {{ t('update_notifier.update_available') }}
      <template #action>
        <v-btn text :loading="updating" @click="update">
          {{ t('common.actions.update') }}
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
const updateSW = ref<((refresh: boolean) => Promise<void>) | undefined>(
  undefined
);
const offlineReady = ref<boolean>(false);
const needRefresh = ref<boolean>(false);
const updating = ref<boolean>(false);

onMounted(async () => {
  // eslint-disable-next-line import/no-unresolved
  const { registerSW } = await import('virtual:pwa-register');
  try {
    set(
      updateSW,
      registerSW({
        immediate: true,
        onRegistered: (registration?: ServiceWorkerRegistration) => {
          setInterval(async () => {
            await registration?.update();
          }, 1000 * 60);
          console.log('Service worker has been registered.');
        },
        onOfflineReady: () => {
          set(offlineReady, true);
          console.log('Offline ready');
        },
        onNeedRefresh: () => {
          set(needRefresh, true);
          console.log('New content is available, please refresh.');
        },
        onRegisterError: (error: any) => {
          console.error('Error during service worker registration:', error);
        }
      })
    );
  } catch {
    console.log('PWA disabled.');
  }
});

const update = async () => {
  set(updating, true);
  const worker = get(updateSW);
  if (worker) {
    await worker(true);
  }
};

const { t } = useI18n();
</script>
