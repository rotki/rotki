<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { TaskType } from '@/types/task-type';
import {
  SYNC_DOWNLOAD,
  SYNC_UPLOAD,
  type SyncAction,
} from '@/types/session/sync';

const { t } = useI18n();
const { logout } = useSessionStore();
const { lastDataUpload } = storeToRefs(usePeriodicStore());
const {
  confirmChecked,
  displaySyncConfirmation,
  syncAction,
  uploadStatus,
  cancelSync,
  forceSync,
  showSyncConfirmation,
  clearUploadStatus,
} = useSync();
const { href, onLinkClick } = useLinks();

const { premium, premiumSync } = storeToRefs(usePremiumStore());

const pending = ref<boolean>(false);
const visible = ref<boolean>(false);

const isDownload = computed<boolean>(() => get(syncAction) === SYNC_DOWNLOAD);
const textChoice = computed<number>(() =>
  get(syncAction) === SYNC_UPLOAD ? 1 : 2,
);
const message = computed<string>(() =>
  get(syncAction) === SYNC_UPLOAD
    ? t('sync_indicator.upload_confirmation.message_upload').toString()
    : t('sync_indicator.upload_confirmation.message_download').toString(),
);

const { resume, pause, counter } = useInterval(600, {
  immediate: false,
  controls: true,
});

const icon = computed(() => {
  const tick = get(counter) % 2 === 0;
  if (get(isDownload))
    return tick ? 'download-cloud-2-line' : 'download-cloud-line';

  return tick ? 'upload-cloud-2-line' : 'upload-cloud-line';
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

const { isTaskRunning } = useTaskStore();
const isSyncing = isTaskRunning(TaskType.FORCE_SYNC);

watch(isSyncing, (current, prev) => {
  if (current !== prev && !current)
    cancelSync();
});

const syncSettingMenuOpen: Ref<boolean> = ref(false);
</script>

<template>
  <Fragment>
    <template v-if="premium">
      <RuiMenu
        id="balances-saved-dropdown"
        v-model="visible"
        menu-class="z-[215]"
        :persistent="syncSettingMenuOpen"
      >
        <template #activator="{ on }">
          <MenuTooltipButton
            :tooltip="tooltip"
            v-on="on"
          >
            <RuiBadge
              :value="!!uploadStatus"
              color="warning"
              dot
              placement="top"
              offset-y="4"
              size="lg"
              class="flex items-center"
            >
              <RuiIcon
                v-if="uploadStatus"
                name="cloud-off-line"
                color="warning"
              />
              <RuiIcon
                v-else-if="!premiumSync"
                name="cloud-off-line"
              />
              <RuiIcon
                v-else-if="isSyncing"
                :name="icon"
                color="primary"
              />
              <RuiIcon
                v-else
                name="cloud-line"
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
            v-if="uploadStatus"
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
                  <i18n path="sync_indicator.db_upload_result.message">
                    <template #reason>
                      <b class="break-words">
                        {{ uploadStatus.message }}
                      </b>
                    </template>
                  </i18n>
                </div>
              </div>
              <RuiButton
                variant="text"
                icon
                size="sm"
                class="-mt-1 -mr-1"
                @click="clearUploadStatus()"
              >
                <RuiIcon name="close-line" />
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
        color="default"
      >
        <template #icon>
          <RuiIcon
            name="lock-line"
            color="primary"
            size="14"
          />
        </template>
        <MenuTooltipButton
          :tooltip="t('sync_indicator.menu_tooltip')"
          :href="href"
          @click="onLinkClick()"
        >
          <RuiIcon name="cloud-line" />
        </MenuTooltipButton>
      </RuiBadge>
    </template>

    <ConfirmDialog
      confirm-type="warning"
      :display="displaySyncConfirmation"
      :title="t('sync_indicator.upload_confirmation.title', textChoice)"
      :message="message"
      :disabled="!confirmChecked"
      :primary-action="
        t('sync_indicator.upload_confirmation.action', textChoice)
      "
      :loading="isSyncing"
      :secondary-action="t('common.actions.cancel')"
      @cancel="cancelSync()"
      @confirm="performSync()"
    >
      <div
        v-if="isDownload"
        class="font-medium mt-3"
        v-text="
          t('sync_indicator.upload_confirmation.message_download_relogin')
        "
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
        confirm
      />
    </ConfirmDialog>
  </Fragment>
</template>
