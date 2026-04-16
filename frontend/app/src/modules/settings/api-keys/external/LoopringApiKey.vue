<script setup lang="ts">
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { Module } from '@/modules/core/common/modules';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { useServiceKeyHandler } from '@/modules/settings/api-keys/external/use-service-key-handler';
import ServiceKey from '@/modules/settings/api-keys/ServiceKey.vue';
import ServiceKeyCard from '@/modules/settings/api-keys/ServiceKeyCard.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { Routes } from '@/router/routes';

const name = 'loopring';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { fetchLoopringBalances } = useBlockchainBalances();
const { actionStatus, useApiKey, confirmDelete, loading, save } = useExternalApiKeys();
const { saveHandler, serviceKeyRef } = useServiceKeyHandler<InstanceType<typeof ServiceKey>>();

const key = useApiKey(name);
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
