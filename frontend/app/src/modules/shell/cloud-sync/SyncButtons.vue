<script setup lang="ts">
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { usePremium } from '@/modules/premium/use-premium';
import { SYNC_DOWNLOAD, SYNC_UPLOAD, type SyncAction } from '@/modules/session/sync';
import { useSync } from '@/modules/session/use-session-sync';

const { pending, disabled = false } = defineProps<{
  pending: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  action: [action: SyncAction];
}>();

const { t } = useI18n({ useScope: 'global' });

const premium = usePremium();
const UPLOAD: SyncAction = SYNC_UPLOAD;
const DOWNLOAD: SyncAction = SYNC_DOWNLOAD;

function action(action: SyncAction) {
  emit('action', action);
}

const { uploadStatus } = useSync();
const { loadingBalancesAndDetection: loading } = useBalancesLoading();
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="grid grid-cols-2 gap-2">
      <RuiTooltip
        :open-delay="400"
        class="w-full"
      >
        <template #activator>
          <RuiButton
            :variant="uploadStatus ? 'default' : 'outlined'"
            color="primary"
            class="w-full"
            data-testid="sync-upload"
            :disabled="!premium || pending || loading || disabled"
            @click="action(UPLOAD)"
          >
            <template #prepend>
              <RuiIcon
                name="lu-cloud-upload"
                size="16"
              />
            </template>
            {{ t('sync_buttons.upload') }}
          </RuiButton>
        </template>
        <span>{{ t('sync_buttons.upload_tooltip') }}</span>
      </RuiTooltip>

      <RuiTooltip
        :open-delay="400"
        class="w-full"
      >
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            class="w-full"
            data-testid="sync-download"
            :disabled="!premium || pending || !!uploadStatus || loading || disabled"
            @click="action(DOWNLOAD)"
          >
            <template #prepend>
              <RuiIcon
                name="lu-cloud-download"
                size="16"
              />
            </template>
            {{ t('sync_buttons.download') }}
          </RuiButton>
        </template>
        <span>{{ t('sync_buttons.download_tooltip') }}</span>
      </RuiTooltip>
    </div>
    <div
      v-if="loading && !pending && !disabled"
      class="text-xs text-rui-text-secondary"
      data-testid="sync-waiting"
    >
      {{ t('sync_buttons.waiting_for_balances') }}
    </div>
  </div>
</template>
