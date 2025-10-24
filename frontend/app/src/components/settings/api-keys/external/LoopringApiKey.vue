<script setup lang="ts">
import ServiceKey from '@/components/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useExternalApiKeys, useServiceKeyHandler } from '@/composables/settings/api-keys/external';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { Routes } from '@/router/routes';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Module } from '@/types/modules';
import { getPublicProtocolImagePath } from '@/utils/file';

const name = 'loopring';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { fetchLoopringBalances } = useBlockchainBalances();
const { actionStatus, apiKey, confirmDelete, loading, save } = useExternalApiKeys(t);
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = apiKey(name);
const status = actionStatus(name);
const isLoopringActive = useArrayIncludes(activeModules, Module.LOOPRING);

const refresh = () => fetchLoopringBalances(true);
const navigateToModules = () => router.push(Routes.SETTINGS_MODULES);
</script>

<template>
  <ServiceKeyCard
    :key-set="!!key"
    :title="t('external_services.loopring.title')"
    :subtitle="t('external_services.loopring.description')"
    :image-src="getPublicProtocolImagePath('loopring.svg')"
    :action-disabled="!serviceKeyRef?.currentValue"
    @confirm="saveHandler()"
  >
    <template #left-buttons>
      <RuiButton
        :disabled="loading || !key"
        color="error"
        variant="text"
        @click="confirmDelete(name, refresh)"
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
      :hint="t('external_services.loopring.hint')"
      :loading="loading"
      :status="status"
      @save="save($event)"
    >
      <RuiAlert
        v-if="key && !isLoopringActive"
        type="warning"
      >
        <div class="flex gap-4 items-center">
          <div class="grow">
            {{ t('external_services.loopring.not_enabled') }}
          </div>
          <RuiButton
            size="sm"
            color="primary"
            @click="navigateToModules()"
          >
            {{ t('external_services.loopring.settings') }}
          </RuiButton>
        </div>
      </RuiAlert>
    </ServiceKey>
  </ServiceKeyCard>
</template>
