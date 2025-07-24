<script setup lang="ts">
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import AskUserUponSizeDiscrepancySetting from '@/components/settings/general/AskUserUponSizeDiscrepancySetting.vue';
import SyncButtons from '@/components/status/sync/SyncButtons.vue';
import SyncSettings from '@/components/status/sync/SyncSettings.vue';
import { useLinks } from '@/composables/links';
import { useSync } from '@/composables/session/sync';
import { useLogout } from '@/modules/account/use-logout';
import { usePeriodicStore } from '@/store/session/periodic';
import { usePremiumStore } from '@/store/session/premium';
import { useTaskStore } from '@/store/tasks';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/types/session/sync';
import { TaskType } from '@/types/task-type';

const { t } = useI18n({ useScope: 'global' });
const { logout } = useLogout();
const { lastDataUpload } = storeToRefs(usePeriodicStore());
const {
  cancelSync,
  clearUploadStatus,
  confirmChecked,
  displaySyncConfirmation,
  forceSync,
  showSyncConfirmation,
  syncAction,
  uploadProgress,
  uploadStatus,
} = useSync();
const { href, onLinkClick } = useLinks();

const { premium, premiumSync } = storeToRefs(usePremiumStore());

const pending = ref<boolean>(false);
const visible = ref<boolean>(false);

const isDownload = computed<boolean>(() => get(syncAction) === SYNC_DOWNLOAD);
const textChoice = computed<number>(() => (get(syncAction) === SYNC_UPLOAD ? 1 : 2));
const message = computed<string>(() =>
  get(syncAction) === SYNC_UPLOAD
    ? t('sync_indicator.upload_confirmation.message_upload')
    : t('sync_indicator.upload_confirmation.message_download'),
);

const { counter, pause, resume } = useInterval(600, {
  controls: true,
  immediate: false,
});

const icon = computed(() => {
  const tick = get(counter) % 2 === 0;
  if (get(isDownload))
    return tick ? 'lu-cloud-download-2-fill' : 'lu-cloud-download-fill';

  return tick ? 'lu-cloud-upload-2-fill' : 'lu-cloud-upload-fill';
});

const uploadProgressIcon = computed<string>(() => {
  const progress = get(uploadProgress);
  if (!progress)
    return 'lu-cloud-fill';

  switch (progress.type) {
    case 'compressing':
      return 'lu-package-2';
    case 'encrypting':
      return 'lu-shield';
    case 'uploading': {
      const tick = get(counter) % 2 === 0;
      return tick ? 'lu-cloud-upload-2-fill' : 'lu-cloud-upload-fill';
    }
    default:
      return 'lu-cloud-fill';
  }
});

const tooltip = computed<string>(() => {
  if (get(uploadStatus)) {
    const title = t('sync_indicator.db_upload_result.title');
    const message = t('sync_indicator.db_upload_result.message', {
      reason: get(uploadStatus)?.message,
    });
    return `${title}: ${message}`;
  }
  return t('sync_indicator.menu_tooltip');
});

const currentProgressText = computed<string>(() => {
  if (!isDefined(uploadProgress)) {
    return '';
  }

  const type = get(uploadProgress).type;
  switch (type) {
    case 'compressing':
      return t('sync_indicator.upload_progress.compressing');
    case 'encrypting':
      return t('sync_indicator.upload_progress.encrypting');
    case 'uploading':
      return t('sync_indicator.upload_progress.uploading');
    default:
      return '';
  }
});

function showConfirmation(action: SyncAction) {
  set(visible, false);
  showSyncConfirmation(action);
}

async function performSync() {
  if (get(syncAction) === SYNC_UPLOAD)
    clearUploadStatus();

  resume();
  set(pending, true);
  await forceSync(logout);
  set(pending, false);
  pause();
}

const { useIsTaskRunning } = useTaskStore();
const isSyncing = useIsTaskRunning(TaskType.FORCE_SYNC);

watch(isSyncing, (current, prev) => {
  if (current !== prev && !current)
    cancelSync();
});

const syncSettingMenuOpen = ref<boolean>(false);
</script>

<template>
  <template v-if="premium">
    <RuiMenu
      id="balances-saved-dropdown"
      v-model="visible"
      menu-class="z-[215]"
      :persistent="syncSettingMenuOpen"
    >
      <template #activator="{ attrs }">
        <MenuTooltipButton
          :tooltip="tooltip"
          v-bind="attrs"
        >
          <RuiBadge
            :model-value="!!uploadStatus"
            color="warning"
            dot
            placement="top"
            offset-y="4"
            size="lg"
            class="flex items-center"
          >
            <RuiIcon
              v-if="uploadStatus"
              name="lu-cloud-off-fill"
              color="warning"
            />
            <RuiIcon
              v-else-if="uploadProgress"
              :name="uploadProgressIcon"
              color="primary"
            />
            <RuiIcon
              v-else-if="isSyncing"
              :name="icon"
              color="primary"
            />
            <RuiIcon
              v-else-if="premiumSync"
              name="lu-cloud-sync-fill"
            />
            <RuiIcon
              v-else
              name="lu-cloud-fill"
            />
          </RuiBadge>
        </MenuTooltipButton>
      </template>
      <div class="p-4 w-[20rem] max-w-[calc(100vw-1rem)] flex flex-col gap-4">
        <div class="flex items-start justify-between">
          <div>
            <div class="font-medium">
              {{ t('sync_indicator.last_data_upload') }}
            </div>
            <div class="text-rui-text-secondary">
              <DateDisplay
                v-if="lastDataUpload"
                :timestamp="lastDataUpload"
              />
              <span v-else>
                {{ t('common.never') }}
              </span>
            </div>
          </div>
          <SyncSettings v-model="syncSettingMenuOpen" />
        </div>
        <RuiAlert
          v-if="uploadProgress"
          type="info"
          outlined
          class="border border-rui-info"
        >
          <div class="flex flex-col gap-2">
            <div class="font-medium leading-5">
              {{ currentProgressText }}
            </div>
            <RuiProgress
              v-if="uploadProgress.type === 'uploading'"
              color="primary"
              :value="(uploadProgress.currentChunk / uploadProgress.totalChunks) * 100"
              show-label
            />
            <div
              v-if="uploadProgress.type === 'uploading'"
              class="text-rui-text-secondary text-sm"
            >
              {{
                t('sync_indicator.upload_progress.chunk', {
                  current: uploadProgress.currentChunk,
                  total: uploadProgress.totalChunks,
                })
              }}
            </div>
          </div>
        </RuiAlert>
        <RuiAlert
          v-else-if="uploadStatus"
          type="warning"
          outlined
          class="border border-rui-warning"
        >
          <div class="flex items-start justify-between gap-1">
            <div>
              <div class="font-medium leading-5">
                {{ t('sync_indicator.db_upload_result.title') }}
              </div>
              <div class="text-rui-text-secondary text-sm">
                <i18n-t
                  scope="global"
                  keypath="sync_indicator.db_upload_result.message"
                  tag="span"
                >
                  <template #reason>
                    <b class="break-words">
                      {{ uploadStatus.message }}
                    </b>
                  </template>
                </i18n-t>
              </div>
            </div>
            <RuiButton
              variant="text"
              icon
              size="sm"
              class="-mt-1 -mr-1"
              @click="clearUploadStatus()"
            >
              <RuiIcon name="lu-x" />
            </RuiButton>
          </div>
        </RuiAlert>
        <SyncButtons
          :pending="pending"
          @action="showConfirmation($event)"
        />
      </div>
    </RuiMenu>
  </template>
  <template v-else>
    <RuiBadge
      placement="top"
      offset-y="12"
      offset-x="-10"
      size="sm"
    >
      <template #icon>
        <RuiIcon
          name="lu-lock-keyhole"
          size="10"
        />
      </template>
      <MenuTooltipButton
        :tooltip="t('sync_indicator.menu_tooltip')"
        :href="href"
        @click="onLinkClick()"
      >
        <RuiIcon name="lu-cloud-fill" />
      </MenuTooltipButton>
    </RuiBadge>
  </template>

  <ConfirmDialog
    confirm-type="warning"
    :display="displaySyncConfirmation"
    :title="t('sync_indicator.upload_confirmation.title', textChoice)"
    :message="message"
    :disabled="!confirmChecked"
    :primary-action="t('sync_indicator.upload_confirmation.action', textChoice)"
    :loading="isSyncing"
    :secondary-action="t('common.actions.cancel')"
    @cancel="cancelSync()"
    @confirm="performSync()"
  >
    <div
      v-if="isDownload"
      class="font-medium mt-3"
      v-text="t('sync_indicator.upload_confirmation.message_download_relogin')"
    />
    <RuiCheckbox
      v-model="confirmChecked"
      class="mt-2"
      color="primary"
      hide-details
    >
      {{ t('sync_indicator.upload_confirmation.confirm_check') }}
    </RuiCheckbox>

    <AskUserUponSizeDiscrepancySetting
      v-if="uploadStatus"
      dialog
      confirm
    />
  </ConfirmDialog>
</template>
