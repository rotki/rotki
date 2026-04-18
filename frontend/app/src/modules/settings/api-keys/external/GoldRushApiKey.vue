<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { externalLinks } from '@shared/external-links';
import CopyButton from '@/components/helper/CopyButton.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useExternalApiKeys, useServiceKeyHandler } from '@/composables/settings/api-keys/external';
import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import { getPublicServiceImagePath } from '@/utils/file';

const { t } = useI18n({ useScope: 'global' });

const name = 'goldrush';

const { actionStatus, apiKey, confirmDelete, loading, save } = useExternalApiKeys(t);
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = apiKey(name);
const status = actionStatus(name);

interface X402WalletInfo {
  address: string;
  chainId: number;
  usdcContract: string;
}

const x402Wallet = ref<X402WalletInfo>();
const x402Loading = ref<boolean>(false);

async function fetchX402Wallet(): Promise<void> {
  set(x402Loading, true);
  try {
    const response = await api.get<X402WalletInfo>('/goldrush/x402_wallet', {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });
    set(x402Wallet, response);
  }
  catch {
    // x402 wallet not available (e.g. user has API key set or not logged in)
  }
  finally {
    set(x402Loading, false);
  }
}

const showX402 = computed<boolean>(() => !get(key) && !!get(x402Wallet));

onMounted(() => {
  startPromise(fetchX402Wallet());
});
</script>

<template>
  <ServiceKeyCard
    :key-set="!!key"
    :title="t('external_services.goldrush.title')"
    :subtitle="t('external_services.goldrush.description')"
    :image-src="getPublicServiceImagePath('goldrush.svg')"
    :action-disabled="!serviceKeyRef?.currentValue"
    @confirm="saveHandler()"
  >
    <template #left-buttons>
      <RuiButton
        :disabled="loading || !key"
        color="error"
        variant="text"
        @click="confirmDelete(name)"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="16"
          />
        </template>
        {{ t('external_services.actions.delete_key') }}
      </RuiButton>
    </template>
    <ServiceKey
      ref="serviceKeyRef"
      hide-actions
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.api_key')"
      :hint="t('external_services.goldrush.hint')"
      :loading="loading"
      :status="status"
      @save="save($event)"
    >
      <i18n-t
        scope="global"
        tag="div"
        class="text-rui-text-secondary text-body-2"
        keypath="external_services.get_api_key"
      >
        <template #link>
          <ExternalLink
            color="primary"
            :url="externalLinks.goldrushApiKey"
          >
            {{ t('common.here') }}
          </ExternalLink>
        </template>
      </i18n-t>
    </ServiceKey>

    <div
      v-if="showX402"
      class="mt-4 rounded-lg border border-rui-warning-lighter bg-rui-warning-lighter/10 p-3 space-y-2"
    >
      <RuiAlert
        type="warning"
        class="text-body-2"
      >
        {{ t('external_services.goldrush.x402.warning') }}
      </RuiAlert>
      <div class="flex items-center gap-2 text-body-2">
        <span class="text-rui-text-secondary font-medium">
          {{ t('external_services.goldrush.x402.address_label') }}:
        </span>
        <code class="flex-1 truncate text-xs font-mono">{{ x402Wallet?.address }}</code>
        <CopyButton
          :value="x402Wallet?.address ?? ''"
          :tooltip="t('external_services.goldrush.x402.copy_tooltip')"
          size="sm"
        />
      </div>
      <div class="text-rui-text-secondary text-body-2">
        {{ t('external_services.goldrush.x402.chain_label') }}
      </div>
    </div>
  </ServiceKeyCard>
</template>
