<script setup lang="ts">
import { msg } from '@/message-key';
import { useCountFormatter } from '@/modules/assets/amount-display/use-count-formatter';
import { usePlanUpgradeLink } from '@/modules/premium/use-plan-upgrade-link';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const {
  count = 0,
  matchMinimumTier = null,
  variant,
} = defineProps<{
  variant: 'bridge' | 'asset-movement';
  /** How many entries are waiting to be matched; 0 (the ignored list) leaves the count out. */
  count?: number;
  matchMinimumTier?: string | null;
}>();

const { t } = useI18n({ useScope: 'global' });

const { currentTier } = usePremiumHelper();
const { upgradeText, upgradeUrl } = usePlanUpgradeLink();
const { formatCount } = useCountFormatter();

/** The plan that unlocks matching, or the product name when the server did not say which plan. */
const tier = computed<string>(() => matchMinimumTier ?? t('premium_settings.title'));

const messageKey = computed<string>(() => {
  if (variant === 'bridge')
    return count > 0 ? msg.$t('bridge_matching.premium.unmatched') : msg.$t('bridge_matching.premium.locked');
  return count > 0 ? msg.$t('asset_movement_matching.premium.unmatched') : msg.$t('asset_movement_matching.premium.locked');
});
</script>

<template>
  <RuiAlert
    type="warning"
    size="sm"
    class="whitespace-break-spaces !py-0.5 !rounded-none"
  >
    <i18n-t
      scope="global"
      :keypath="messageKey"
      :plural="count"
    >
      <template #count>
        {{ formatCount(count) }}
      </template>
      <template #tier>
        <strong>{{ tier }}</strong>
      </template>
      <template #currentTier>
        <strong>{{ currentTier }}</strong>
      </template>
      <template #link>
        <ExternalLink
          :text="upgradeText"
          :url="upgradeUrl"
          premium
          color="primary"
        />
      </template>
    </i18n-t>
  </RuiAlert>
</template>
