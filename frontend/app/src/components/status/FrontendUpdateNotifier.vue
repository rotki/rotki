<template>
  <div v-if="needRefresh">
    <v-dialog :value="true" persistent max-width="500">
      <card>
        <div class="pt-5 text-center">
          {{ t('update_notifier.update_available') }}
          <v-btn
            depressed
            class="ml-6"
            color="primary"
            :loading="updating"
            @click="update"
          >
            {{ t('common.actions.update') }}
          </v-btn>
        </div>
      </card>
    </v-dialog>
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

watch(needRefresh, async needRefresh => {
  if (needRefresh) {
    await update();
  }
});

const update = async () => {
  set(updating, true);
  const worker = get(updateSW);
  if (worker) {
    await worker(true);
  }
  set(updating, false);
};

const { t } = useI18n();
</script>
