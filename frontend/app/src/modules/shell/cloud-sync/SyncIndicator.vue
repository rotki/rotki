<script setup lang="ts">
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import AskUserUponSizeDiscrepancySetting from '@/modules/settings/general/AskUserUponSizeDiscrepancySetting.vue';
import SyncButtons from '@/modules/shell/cloud-sync/SyncButtons.vue';
import SyncSettings from '@/modules/shell/cloud-sync/SyncSettings.vue';
import SyncUploadStatusAlert from '@/modules/shell/cloud-sync/SyncUploadStatusAlert.vue';
import { useSyncIndicator } from '@/modules/shell/cloud-sync/use-sync-indicator';
import ConfirmDialog from '@/modules/shell/components/dialogs/ConfirmDialog.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import { useLinks } from '@/modules/shell/layout/use-links';

const { t } = useI18n({ useScope: 'global' });

const { premium, premiumSync } = storeToRefs(usePremiumStore());
const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
const { href, onLinkClick } = useLinks();

const {
  cancelForceSync,
  cancelSync,
  clearUploadStatus,
  cloudBackupAllowed,
  confirmChecked,
  currentProgressText,
  displaySyncConfirmation,
  icon,
  isDownload,
  isSyncing,
  message,
  modelSyncSettingMenuOpen,
  modelVisible,
  pending,
  performSync,
  showConfirmation,
  textChoice,
  tooltip,
  uploadProgress,
  uploadProgressIcon,
  uploadStatus,
} = useSyncIndicator();
</script>

<template>
  <template v-if="premium">
    <RuiMenu
      id="balances-saved-dropdown"
      v-model="modelVisible"
      :class-names="{ menu: 'z-[215]' }"
      :persistent="modelSyncSettingMenuOpen"
    >
      <template #activator="{ attrs }">
        <MenuTooltipButton
          :tooltip="tooltip"
          v-bind="attrs"
        >
          <RuiBadge
            :model-value="!!uploadStatus || !cloudBackupAllowed"
            :color="!cloudBackupAllowed ? undefined : 'warning'"
            :dot="cloudBackupAllowed"
            placement="top"
            :offset-y="cloudBackupAllowed ? 4 : 12"
            :offset-x="cloudBackupAllowed ? undefined : -6"
            :size="cloudBackupAllowed ? 'lg' : 'sm'"
            class="flex items-center"
          >
            <template
              v-if="!cloudBackupAllowed"
              #icon
            >
              <RuiIcon
                name="lu-lock-keyhole"
                size="10"
              />
            </template>
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
          <SyncSettings
            v-model="modelSyncSettingMenuOpen"
            :disabled="!cloudBackupAllowed"
          />
        </div>
        <RuiAlert
          v-if="!cloudBackupAllowed"
          type="info"
          outlined
          class="border border-rui-info"
        >
          <div class="text-sm">
            {{ t('sync_indicator.cloud_backup_unavailable') }}
          </div>
          <div class="flex flex-row-reverse -mb-1">
            <RuiButton
              variant="text"
              color="primary"
              size="sm"
              :href="href"
              @click="onLinkClick()"
            >
              {{ t('sync_indicator.cloud_backup_upgrade') }}
            </RuiButton>
          </div>
        </RuiAlert>
        <RuiAlert
          v-else-if="uploadProgress"
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
          <div
            v-if="pending && uploadProgress"
            class="flex flex-row-reverse -mb-1"
          >
            <RuiButton
              variant="text"
              color="primary"
              data-testid="cancel-force-sync"
              @click="cancelForceSync()"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>
          </div>
        </RuiAlert>
        <SyncUploadStatusAlert
          v-else-if="uploadStatus"
          :message="uploadStatus.message"
          @clear="clearUploadStatus()"
        />
        <SyncButtons
          :pending="pending"
          :disabled="!cloudBackupAllowed"
          @action="showConfirmation($event)"
        />
      </div>
    </RuiMenu>
  </template>
  <template v-else>
    <RuiBadge
      placement="top"
      offset-y="12"
      offset-x="-6"
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
