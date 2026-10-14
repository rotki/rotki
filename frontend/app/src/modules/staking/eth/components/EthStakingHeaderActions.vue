<script setup lang="ts">
import AccountFormApiKeyOffer from '@/modules/accounts/management/AccountFormApiKeyOffer.vue';
import { useApiKeyNotice } from '@/modules/accounts/management/use-api-key-notice';
import { Module } from '@/modules/core/common/modules';
import ModuleSettingsMenu from '@/modules/settings/modules/ModuleSettingsMenu.vue';
import StakingRefreshActions from '@/modules/staking/components/StakingRefreshActions.vue';

/**
 * The page's Refresh, then the settings: the ETH staking module and, while the page runs without
 * it, the optional Beaconcha.in key. The settings button carries a dot while the key offer has not
 * been answered.
 */
const { optionalApiKeyService } = defineProps<{
  refreshing: boolean;
  syncingHistory: boolean;
  /** The chain the history sync queries, named in its menu entry. */
  chainName: string;
  optionalApiKeyService?: 'beaconchain';
}>();

const emit = defineEmits<{
  'refresh': [];
  'sync-history': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { dismissed } = useApiKeyNotice(() => optionalApiKeyService);

const attentionHint = computed<string | undefined>(() =>
  optionalApiKeyService && !get(dismissed) ? t('staking_page.eth.api_key_hint') : undefined,
);
</script>

<template>
  <StakingRefreshActions
    :refreshing="refreshing"
    :syncing-history="syncingHistory"
    :chain-name="chainName"
    :tooltip="t('premium_components.staking.refresh')"
    test-id-prefix="eth-staking"
    @refresh="emit('refresh')"
    @sync-history="emit('sync-history')"
  >
    <ModuleSettingsMenu
      :modules="[Module.ETH2]"
      :attention-hint="attentionHint"
    >
      <AccountFormApiKeyOffer
        v-if="optionalApiKeyService"
        :service="optionalApiKeyService"
      />
    </ModuleSettingsMenu>
  </StakingRefreshActions>
</template>
