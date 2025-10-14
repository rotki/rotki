<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import { useInterop } from '@/composables/electron-interop';
import { useUpdateChecker } from '@/modules/session/use-update-checker';

const downloadReady = ref(false);
const downloading = ref(false);
const restarting = ref(false);
const percentage = ref(0);
const error = ref('');

const { showUpdatePopup } = useUpdateChecker();
const { downloadUpdate, installUpdate, isPackaged } = useInterop();

const { t } = useI18n({ useScope: 'global' });

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
</script>

<template>
  <RuiNotification
    v-if="isPackaged"
    :model-value="showUpdatePopup"
    :timeout="-1"
    class="top-[3.5rem] text-rui-text !bg-transparent"
    width="380px"
  >
    <RuiCard rounded="md">
      <div
        v-if="!restarting"
        class="flex items-center gap-4"
      >
        <div class="w-10 h-10">
          <RuiIcon
            v-if="error"
            size="40"
            color="error"
            name="lu-circle-alert"
          />
          <RuiIcon
            v-else-if="!downloadReady && !downloading"
            size="40"
            color="primary"
            name="lu-circle-arrow-up"
          />
          <RuiIcon
            v-else
            size="40"
            color="primary"
            name="lu-circle-arrow-down"
          />
        </div>
        <div class="text-body-2">
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
              scope="global"
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
        :value="percentage"
        show-label
      />

      <div class="flex justify-end mt-4">
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
    </RuiCard>
  </RuiNotification>
</template>
