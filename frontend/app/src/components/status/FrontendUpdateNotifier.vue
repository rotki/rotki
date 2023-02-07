<script setup lang="ts">
import { logger } from '@/utils/logging';

const updateSW = ref<((refresh: boolean) => Promise<void>) | undefined>(
  undefined
);
const offlineReady = ref<boolean>(false);
const needRefresh = ref<boolean>(false);
const updating = ref<boolean>(false);

onMounted(async () => {
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
          logger.info('Service worker has been registered.');
        },
        onOfflineReady: () => {
          set(offlineReady, true);
          logger.info('Offline ready');
        },
        onNeedRefresh: () => {
          set(needRefresh, true);
          logger.info('New content is available, please refresh.');
        },
        onRegisterError: (error: any) => {
          logger.error('Error during service worker registration:', error);
        }
      })
    );
  } catch {
    logger.info('PWA disabled.');
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
