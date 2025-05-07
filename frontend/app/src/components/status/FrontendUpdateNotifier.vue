<script setup lang="ts">
import { logger } from '@/utils/logging';

const updateSW = ref<((refresh: boolean) => Promise<void>) | undefined>(undefined);
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
        onNeedRefresh: () => {
          set(needRefresh, true);
          logger.info('New content is available, please refresh.');
        },
        onOfflineReady: () => {
          set(offlineReady, true);
          logger.info('Offline ready');
        },
        onRegistered: (registration?: ServiceWorkerRegistration) => {
          setInterval(async () => {
            await registration?.update();
          }, 1000 * 60);
          logger.info('Service worker has been registered.');
        },
        onRegisterError: (error: any) => {
          logger.error('Error during service worker registration:', error);
        },
      }),
    );
  }
  catch {
    logger.info('PWA disabled.');
  }
});

watch(needRefresh, async (needRefresh) => {
  if (needRefresh)
    await update();
});

async function update() {
  set(updating, true);
  const worker = get(updateSW);
  if (worker)
    await worker(true);

  set(updating, false);
}

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div v-if="needRefresh">
    <RuiDialog
      :model-value="true"
      persistent
      max-width="500"
    >
      <RuiCard content-class="flex flex-col md:flex-row gap-4 text-center items-center justify-between">
        {{ t('update_notifier.update_available') }}
        <RuiButton
          color="primary"
          :loading="updating"
          @click="update()"
        >
          {{ t('common.actions.update') }}
        </RuiButton>
      </RuiCard>
    </RuiDialog>
  </div>
</template>
