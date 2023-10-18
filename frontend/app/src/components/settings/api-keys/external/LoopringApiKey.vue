<script setup lang="ts">
import { Module } from '@/types/modules';

const name = 'loopring';

const { t } = useI18n();

const { activeModules } = storeToRefs(useGeneralSettingsStore());
const { fetchLoopringBalances } = useEthBalancesStore();
const { loading, apiKey, actionStatus, save, confirmDelete } =
  useExternalApiKeys(t);

const key = apiKey(name);
const status = actionStatus(name);
const isLoopringActive = useArrayIncludes(activeModules, Module.LOOPRING);

const refresh = () => fetchLoopringBalances(true);
const navigateToModules = () => useRouter().push('/settings/modules');
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('external_services.loopring.title') }}
    </template>
    <template #subheader>
      {{ t('external_services.loopring.description') }}
    </template>

    <ServiceKey
      :api-key="key"
      :name="name"
      :data-cy="name"
      :label="t('external_services.loopring.label')"
      :hint="t('external_services.loopring.hint')"
      :loading="loading"
      :tooltip="t('external_services.loopring.delete_tooltip')"
      :status="status"
      @save="save($event)"
      @delete-key="confirmDelete($event, refresh)"
    >
      <RuiAlert v-if="key && !isLoopringActive" type="warning">
        <div class="flex gap-4 items-center">
          <div class="grow">
            {{ t('external_services.loopring.not_enabled') }}
          </div>
          <RuiButton size="sm" color="primary" @click="navigateToModules()">
            {{ t('external_services.loopring.settings') }}
          </RuiButton>
        </div>
      </RuiAlert>
    </ServiceKey>
  </RuiCard>
</template>
