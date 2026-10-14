<script setup lang="ts">
import AccountFormApiKeyAlertContent from '@/modules/accounts/management/AccountFormApiKeyAlertContent.vue';
import { type ApiKeyNoticeService, useApiKeyNotice } from '@/modules/accounts/management/use-api-key-notice';

/**
 * An optional API key offer, as a section of a page's settings menu.
 *
 * Reserved for keys the page works without. A page that is actually missing a data source stays on
 * the banner, because prominence should follow severity; tucking a "there is no data" state into a
 * menu would hide it. The section stays in the menu for good; putting the reminder away only stops
 * the settings button from asking for a look.
 */
const { service } = defineProps<{
  service: ApiKeyNoticeService;
}>();

const { t } = useI18n({ useScope: 'global' });

const { dismiss, dismissed } = useApiKeyNotice(() => service);

const title = computed<string>(() => {
  if (service === 'etherscan')
    return t('external_services.etherscan.title');

  if (service === 'consensusRpc')
    return t('external_services.api_key_menu.consensus_rpc_title');

  if (service === 'beaconchain')
    return t('external_services.beaconchain.title');

  if (service === 'helius')
    return t('external_services.helius.title');

  return t('external_services.blockscout.title');
});
</script>

<template>
  <section
    class="flex flex-col gap-1 text-body-2"
    data-testid="api-key-offer"
  >
    <div class="flex items-center gap-2">
      <h3 class="text-subtitle-2 font-medium m-0">
        {{ title }}
      </h3>
      <RuiChip
        size="sm"
        variant="tonal"
        color="info"
      >
        {{ t('external_services.api_key_menu.optional') }}
      </RuiChip>
    </div>

    <div class="text-rui-text-secondary">
      <AccountFormApiKeyAlertContent :service="service" />
    </div>

    <div
      v-if="!dismissed"
      class="flex justify-end"
    >
      <RuiButton
        variant="text"
        color="secondary"
        size="sm"
        data-testid="api-key-offer-dismiss"
        @click="dismiss()"
      >
        {{ t('external_services.api_key_menu.stop_reminding') }}
      </RuiButton>
    </div>
  </section>
</template>
