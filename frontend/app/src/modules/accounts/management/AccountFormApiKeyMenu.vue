<script setup lang="ts">
import AccountFormApiKeyAlertContent from '@/modules/accounts/management/AccountFormApiKeyAlertContent.vue';
import { logger } from '@/modules/core/common/logging/logging';
import { useFrontendSettingsWriter } from '@/modules/settings/use-frontend-settings-writer';
import { useSetting } from '@/modules/settings/use-setting';

/**
 * An optional API key offer, behind a button instead of a banner.
 *
 * Reserved for keys the page works without. A page that is actually missing a data source stays on
 * the banner, because prominence should follow severity; demoting a "there is no data" state to
 * something you have to click would hide it.
 *
 * Since the prompt is an offer rather than a fault, it is dismissible and the dismissal is
 * remembered, so it does not become permanent chrome for someone who has decided against the key.
 */
const { service } = defineProps<{
  service: 'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc' | 'blockscout';
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const activator = useTemplateRef<HTMLElement>('activator');
const panel = useTemplateRef<HTMLElement>('panel');

const dismissed = useSetting('dismissedApiKeyNotices');
const { updateFrontendSetting } = useFrontendSettingsWriter();

const visible = computed<boolean>(() => !get(dismissed).includes(service));

/** Names the subject, so the popover does not open as an unheaded paragraph. */
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

async function dismiss(): Promise<void> {
  set(open, false);
  const current = get(dismissed);
  if (current.includes(service))
    return;

  const status = await updateFrontendSetting({ dismissedApiKeyNotices: [...current, service] });
  if (!status.success)
    logger.error(`failed to dismiss the ${service} api key notice: ${status.message}`);
}

// `RuiMenu` supplies neither the disclosure semantics nor the focus move, so both are wired here.
// Without the move, the popover is teleported to the end of the document and a keyboard user
// reaches its link only after tabbing through the rest of the page.
watch(open, async (isOpen) => {
  await nextTick();
  if (isOpen)
    get(panel)?.focus();
  else
    get(activator)?.focus();
});
</script>

<template>
  <RuiMenu
    v-if="visible"
    v-model="open"
    menu-class="w-[26rem] max-w-[90vw]"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiButton
        ref="activator"
        variant="outlined"
        color="info"
        size="lg"
        class="!rounded-full"
        aria-haspopup="dialog"
        :aria-expanded="open"
        data-testid="api-key-menu-activator"
        v-bind="attrs"
      >
        <template #prepend>
          <RuiIcon name="lu-info" />
        </template>
        {{ t('external_services.api_key_menu.optional') }}
      </RuiButton>
    </template>

    <div
      ref="panel"
      role="dialog"
      tabindex="-1"
      :aria-label="title"
      class="p-4 flex flex-col gap-2 text-body-2 focus:outline-none"
      data-testid="api-key-menu-content"
    >
      <div class="font-medium text-rui-text">
        {{ title }}
      </div>

      <AccountFormApiKeyAlertContent :service="service" />

      <div class="flex justify-end -mb-1 mt-1">
        <RuiButton
          variant="text"
          color="secondary"
          size="sm"
          data-testid="api-key-menu-dismiss"
          @click="dismiss()"
        >
          {{ t('external_services.api_key_menu.dismiss') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
