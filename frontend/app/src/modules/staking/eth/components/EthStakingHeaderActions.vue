<script setup lang="ts">
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
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
  /** Staking events are being queried without the page's Refresh, shown as a note beside it. */
  queryingEvents: boolean;
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
  <span
    role="status"
    class="sr-only"
    data-testid="eth-staking-querying-events-status"
  >
    <template v-if="queryingEvents">
      {{ t('staking_page.eth.querying_events') }}
    </template>
  </span>
  <div
    v-if="queryingEvents"
    class="flex items-center gap-2 text-caption text-rui-text-secondary"
    aria-hidden="true"
    data-testid="eth-staking-querying-events"
  >
    <RuiProgress
      circular
      variant="indeterminate"
      color="primary"
      size="16"
      thickness="2"
    />
    {{ t('staking_page.eth.querying_events') }}
  </div>
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
