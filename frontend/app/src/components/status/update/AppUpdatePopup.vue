<script setup lang="ts">
const releaseNotesLink = 'https://github.com/rotki/rotki/releases';

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

const dismiss = () => {
  set(showUpdatePopup, false);
  setTimeout(() => {
    set(error, '');
    set(downloading, false);
    set(downloadReady, false);
    set(percentage, 0);
  }, 400);
};

const update = async () => {
  set(downloading, true);
  const downloaded = await downloadUpdate(progress => {
    set(percentage, progress);
  });
  set(downloading, false);
  if (downloaded) {
    set(downloadReady, true);
    set(showUpdatePopup, true);
  } else {
    set(error, t('update_popup.download_failed.message'));
  }
};

const install = async () => {
  set(downloadReady, false);
  set(restarting, true);

  const result = await installUpdate();
  if (typeof result !== 'boolean') {
    set(
      error,
      t('update_popup.install_failed.message', {
        message: result
      })
    );
  }
};

onMounted(async () => {
  if (isPackaged) {
    await checkForUpdate();
  }
});
</script>

<template>
  <VSnackbar
    v-if="isPackaged"
    :value="showUpdatePopup"
    class="update-popup m-4"
    :timeout="-1"
    light
    top
    multi-line
    vertical
    right
    app
    rounded
    width="380px"
  >
    <div v-if="!restarting" class="flex items-center gap-4">
      <RuiIcon v-if="error" size="40" color="error" name="error-warning-line" />
      <RuiIcon
        v-else-if="!downloadReady && !downloading"
        size="40"
        color="primary"
        name="arrow-up-circle-line"
      />
      <RuiIcon v-else size="40" color="primary" name="arrow-down-circle-line" />
      <div class="text-body-1">
        <span v-if="error" class="text-rui-error">
          {{ error }}
        </span>
        <span v-else-if="downloading">
          {{ t('update_popup.download_progress') }}
        </span>
        <div v-else-if="!downloadReady">
          <i18n tag="div" path="update_popup.messages">
            <template #releaseNotes>
              <ExternalLink
                :text="t('update_popup.release_notes')"
                :url="releaseNotesLink"
              />
            </template>
          </i18n>
          <div>{{ t('update_popup.download_nudge') }}</div>
        </div>
        <span v-else>{{ t('update_popup.downloaded') }}</span>
      </div>
    </div>
    <div v-else class="flex items-center gap-4">
      <RuiProgress
        color="primary"
        thickness="2"
        variant="indeterminate"
        circular
      />
      <div class="text-body-1">{{ t('update_popup.restart') }}</div>
    </div>

    <RuiProgress
      v-if="downloading"
      class="mt-4"
      color="primary"
      :value="percentage"
      show-label
    />

    <template #action="{ attrs }">
      <RuiButton
        v-if="error"
        variant="text"
        color="primary"
        v-bind="attrs"
        @click="dismiss()"
      >
        {{ t('common.actions.dismiss') }}
      </RuiButton>
      <div v-else-if="!downloading && !restarting" class="flex gap-2">
        <RuiButton
          variant="text"
          color="primary"
          v-bind="attrs"
          @click="dismiss()"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          v-if="!downloadReady"
          color="primary"
          v-bind="attrs"
          @click="update()"
        >
          {{ t('common.actions.update') }}
        </RuiButton>
        <RuiButton v-else color="primary" v-bind="attrs" @click="install()">
          {{ t('common.actions.install') }}
        </RuiButton>
      </div>
    </template>
  </VSnackbar>
</template>
