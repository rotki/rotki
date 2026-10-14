<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import PremiumPanel from '@/modules/premium/settings/PremiumPanel.vue';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import AskUserUponSizeDiscrepancySetting from '@/modules/settings/general/AskUserUponSizeDiscrepancySetting.vue';
import AutomaticSyncSetting from '@/modules/shell/cloud-sync/AutomaticSyncSetting.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const { disabled = false } = defineProps<{
  /** While the key is replaced, sync waits for it. */
  disabled?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { allowed: cloudBackupAllowed } = useFeatureAccess(PremiumFeature.CLOUD_BACKUP);
const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
</script>

<template>
  <PremiumPanel
    :title="t('premium_settings.sync.title')"
    :description="t('premium_settings.sync.description')"
  >
    <AutomaticSyncSetting :disabled="disabled || !cloudBackupAllowed" />

    <i18n-t
      v-if="!cloudBackupAllowed"
      scope="global"
      tag="p"
      keypath="premium_settings.cloud_backup_unavailable"
      class="m-0 text-sm text-rui-text-secondary"
    >
      <template #link>
        <ExternalLink
          :url="externalLinks.manageSubscriptions"
          :text="t('premium_settings.cloud_backup_upgrade_link')"
          color="primary"
        />
      </template>
    </i18n-t>

    <div class="border-t border-rui-divider" />

    <dl class="m-0 flex flex-col gap-1">
      <dt class="text-sm text-rui-text-secondary">
        {{ t('premium_settings.sync.last_upload') }}
      </dt>
      <dd
        class="m-0 text-base font-medium text-rui-text"
        data-testid="premium-last-upload"
      >
        <TimeAgoDisplay
          v-if="lastDataUpload"
          :timestamp="lastDataUpload"
        />
        <span v-else>{{ t('premium_settings.sync.never') }}</span>
      </dd>
    </dl>

    <AskUserUponSizeDiscrepancySetting dialog />
  </PremiumPanel>
</template>
