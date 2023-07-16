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
    class="update-popup"
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
    <VRow v-if="!restarting" align="center">
      <VCol cols="auto">
        <VIcon v-if="error" large color="error">
          mdi-alert-circle-outline
        </VIcon>
        <VIcon v-else-if="!downloadReady && !downloading" large color="primary">
          mdi-arrow-up-bold-circle
        </VIcon>
        <VIcon v-else large color="primary">mdi-arrow-down-bold-circle</VIcon>
      </VCol>
      <VCol class="text-body-1">
        <span v-if="error" class="error--text">
          {{ error }}
        </span>
        <span v-else-if="downloading">
          {{ t('update_popup.download_progress') }}
        </span>
        <div v-else-if="!downloadReady">
          <I18n tag="div" path="update_popup.messages">
            <template #releaseNotes>
              <BaseExternalLink
                :text="t('update_popup.release_notes')"
                :href="releaseNotesLink"
              />
            </template>
          </I18n>
          <div>{{ t('update_popup.download_nudge') }}</div>
        </div>
        <span v-else>{{ t('update_popup.downloaded') }}</span>
      </VCol>
    </VRow>
    <VRow v-else align="center">
      <VCol cols="auto">
        <VIcon large color="primary"> mdi-spin mdi-loading </VIcon>
      </VCol>
      <VCol class="text-body-1">{{ t('update_popup.restart') }}</VCol>
    </VRow>

    <VProgressLinear
      v-if="downloading"
      :value="percentage"
      class="mt-2"
      color="primary"
      height="25"
    >
      <template #default="{ value }">
        <strong class="white--text">
          {{ t('update_popup.progress', { percentage: Math.ceil(value) }) }}
        </strong>
      </template>
    </VProgressLinear>

    <template #action="{ attrs }">
      <div v-if="error">
        <VBtn text v-bind="attrs" @click="dismiss()">
          {{ t('common.actions.dismiss') }}
        </VBtn>
      </div>
      <div v-else-if="!downloading && !restarting">
        <VBtn text v-bind="attrs" @click="dismiss()">
          {{ t('common.actions.cancel') }}
        </VBtn>
        <VBtn
          v-if="!downloadReady"
          color="primary"
          text
          v-bind="attrs"
          @click="update()"
        >
          {{ t('common.actions.update') }}
        </VBtn>
        <VBtn v-else color="primary" text v-bind="attrs" @click="install()">
          {{ t('common.actions.install') }}
        </VBtn>
      </div>
    </template>
  </VSnackbar>
</template>

<style scoped lang="scss">
.update-popup {
  /* stylelint-disable selector-class-pattern,selector-nested-pattern */

  :deep(.v-snack__wrapper) {
    margin: 16px;
    width: 400px;
    box-shadow: 0 2px 12px rgba(74, 91, 120, 0.1) !important;
  }
  /* stylelint-enable selector-class-pattern,selector-nested-pattern */
}
</style>
