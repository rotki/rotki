<script setup lang="ts">
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import SyncButtons from '@/modules/shell/cloud-sync/SyncButtons.vue';
import SyncConfirmation from '@/modules/shell/cloud-sync/SyncConfirmation.vue';
import SyncSettings from '@/modules/shell/cloud-sync/SyncSettings.vue';
import { useSyncIndicator } from '@/modules/shell/cloud-sync/use-sync-indicator';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
import MenuTooltipButton from '@/modules/shell/components/MenuTooltipButton.vue';
import { useLinks } from '@/modules/shell/layout/use-links';

const { t } = useI18n({ useScope: 'global' });

const { premium, premiumSync } = storeToRefs(usePremiumStore());
const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
const { href, onLinkClick } = useLinks();

const {
  cancelSync,
  cloudBackupAllowed,
  confirmChecked,
  displaySyncConfirmation,
  icon,
  isDownload,
  isSyncing,
  modelSyncSettingMenuOpen,
  modelVisible,
  pending,
  performSync,
  showConfirmation,
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
              name="lu-cloud-off"
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
              name="lu-cloud-sync-auto"
            />
            <RuiIcon
              v-else
              name="lu-cloud"
            />
          </RuiBadge>
        </MenuTooltipButton>
      </template>
      <div class="p-4 w-80 max-w-[calc(100vw-1rem)] flex flex-col gap-4">
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-col gap-0.5">
            <div class="font-medium text-rui-text">
              {{ t('premium_settings.sync.title') }}
            </div>
            <div
              class="text-sm text-rui-text-secondary"
              data-testid="sync-last-upload"
            >
              {{ t('premium_settings.sync.last_upload') }}:
              <TimeAgoDisplay
                v-if="lastDataUpload"
                :timestamp="lastDataUpload"
              />
              <span v-else>{{ t('common.never') }}</span>
            </div>
          </div>
          <SyncSettings
            v-model="modelSyncSettingMenuOpen"
            :disabled="!cloudBackupAllowed"
          />
        </div>
        <div
          v-if="!cloudBackupAllowed"
          class="text-sm text-rui-text-secondary"
          data-testid="sync-unavailable"
        >
          {{ t('sync_indicator.cloud_backup_unavailable') }}
          <a
            class="text-rui-primary underline"
            :href="href"
            @click="onLinkClick()"
          >
            {{ t('sync_indicator.cloud_backup_upgrade') }}
          </a>
        </div>
        <div
          v-else-if="isSyncing"
          class="flex items-center gap-2 text-sm text-rui-text-secondary"
          data-testid="sync-running"
        >
          <RuiProgress
            variant="indeterminate"
            circular
            size="14"
            thickness="2"
            color="primary"
          />
          {{ t('sync_indicator.status.running') }}
        </div>
        <div
          v-else-if="uploadStatus"
          class="flex items-start gap-2 text-sm text-rui-warning"
          data-testid="sync-last-failed"
        >
          <RuiIcon
            name="lu-triangle-alert"
            size="14"
            class="shrink-0 mt-0.5"
          />
          {{ t('sync_indicator.status.failed') }}
        </div>
        <SyncConfirmation
          v-if="displaySyncConfirmation"
          v-model:checked="confirmChecked"
          :download="isDownload"
          :syncing="isSyncing"
          :size-discrepancy="!!uploadStatus"
          @cancel="cancelSync()"
          @confirm="performSync()"
        />
        <SyncButtons
          v-else
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
        <RuiIcon name="lu-cloud" />
      </MenuTooltipButton>
    </RuiBadge>
  </template>
</template>
