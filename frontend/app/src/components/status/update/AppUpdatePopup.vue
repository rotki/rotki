<script setup lang="ts">
import { externalLinks } from '@/data/external-links';

const downloadReady = ref(false);
const downloading = ref(false);
const restarting = ref(false);
const percentage = ref(0);
const error = ref('');

const store = useSessionStore();
const { showUpdatePopup } = storeToRefs(store);
const { checkForUpdate } = store;
const { downloadUpdate, isPackaged, installUpdate } = useInterop();

const { t } = useI18n();

function dismiss() {
  set(showUpdatePopup, false);
  setTimeout(() => {
    set(error, '');
    set(downloading, false);
    set(downloadReady, false);
    set(percentage, 0);
  }, 400);
}

async function update() {
  set(downloading, true);
  const downloaded = await downloadUpdate((progress) => {
    set(percentage, progress);
  });
  set(downloading, false);
  if (downloaded) {
    set(downloadReady, true);
    set(showUpdatePopup, true);
  }
  else {
    set(error, t('update_popup.download_failed.message'));
  }
}

async function install() {
  set(downloadReady, false);
  set(restarting, true);

  const result = await installUpdate();
  if (typeof result !== 'boolean') {
    set(
      error,
      t('update_popup.install_failed.message', {
        message: result,
      }),
    );
  }
}

onMounted(async () => {
  if (isPackaged)
    await checkForUpdate();
});
</script>

<template>
  <RuiNotification
    v-if="isPackaged"
    :model-value="showUpdatePopup"
    :timeout="-1"
    class="top-[3.5rem]"
    width="380px"
  >
    <div class="p-2">
      <div
        v-if="!restarting"
        class="flex items-center gap-4"
      >
        <RuiIcon
          v-if="error"
          size="40"
          color="error"
          name="error-warning-line"
        />
        <RuiIcon
          v-else-if="!downloadReady && !downloading"
          size="40"
          color="primary"
          name="arrow-up-circle-line"
        />
        <RuiIcon
          v-else
          size="40"
          color="primary"
          name="arrow-down-circle-line"
        />
        <div class="text-body-1">
          <span
            v-if="error"
            class="text-rui-error"
          >
            {{ error }}
          </span>
          <span v-else-if="downloading">
            {{ t('update_popup.download_progress') }}
          </span>
          <div v-else-if="!downloadReady">
            <i18n-t
              tag="div"
              keypath="update_popup.messages"
            >
              <template #releaseNotes>
                <ExternalLink
                  :text="t('update_popup.release_notes')"
                  :url="externalLinks.releases"
                />
              </template>
            </i18n-t>
            <div>{{ t('update_popup.download_nudge') }}</div>
          </div>
          <span v-else>{{ t('update_popup.downloaded') }}</span>
        </div>
      </div>
      <div
        v-else
        class="flex items-center gap-4"
      >
        <RuiProgress
          color="primary"
          thickness="2"
          variant="indeterminate"
          circular
        />
        <div class="text-body-1">
          {{ t('update_popup.restart') }}
        </div>
      </div>

      <RuiProgress
        v-if="downloading"
        class="mt-4"
        color="primary"
        :model-value="percentage"
        show-label
      />

      <div class="flex justify-end">
        <RuiButton
          v-if="error"
          variant="text"
          color="primary"
          @click="dismiss()"
        >
          {{ t('common.actions.dismiss') }}
        </RuiButton>
        <div
          v-else-if="!downloading && !restarting"
          class="flex gap-2"
        >
          <RuiButton
            variant="text"
            color="primary"
            @click="dismiss()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
          <RuiButton
            v-if="!downloadReady"
            color="primary"
            @click="update()"
          >
            {{ t('common.actions.update') }}
          </RuiButton>
          <RuiButton
            v-else
            color="primary"
            @click="install()"
          >
            {{ t('common.actions.install') }}
          </RuiButton>
        </div>
      </div>
    </div>
  </RuiNotification>
</template>
