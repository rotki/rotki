<script setup lang="ts">
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { DECENTRALIZED_EXCHANGES } from '@/modules/core/common/modules';
import { Purgeable } from '@/modules/session/purge';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { usePurgeData } from '@/modules/settings/data-security/data-management/use-purge-data';
import DefiModuleSelector from '@/modules/settings/modules/DefiModuleSelector.vue';
import ActionStatusIndicator from '@/modules/shell/components/error/ActionStatusIndicator.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  centralizedExchangePurgeTypeOptions,
  chainsSelection,
  exchanges,
  modelCentralizedExchange,
  modelCentralizedExchangeDataType,
  modelChain,
  modelDecentralizedExchange,
  modelModule,
  modelSource,
  pending,
  purgeable,
  purgeableModules,
  showConfirmation,
  status,
} = usePurgeData();
</script>

<template>
  <SettingsItem action-key="purgeData">
    <template #title>
      {{ t('data_management.purge_data.title') }}
    </template>
    <template #subtitle>
      {{ t('data_management.purge_data.subtitle') }}
    </template>
    <div class="flex flex-col gap-4">
      <RuiAutoComplete
        v-model="modelSource"
        variant="outlined"
        :label="t('purge_selector.label')"
        :options="purgeable"
        text-attr="text"
        key-attr="id"
        hide-details
        :disabled="pending"
        data-testid="purge-source"
      />
      <ChainSelect
        v-if="modelSource === Purgeable.TRANSACTIONS"
        v-model="modelChain"
        clearable
        persistent-hint
        :items="chainsSelection"
        :label="t('purge_selector.chain_to_clear.label')"
        :hint="t('purge_selector.chain_to_clear.hint')"
      />
      <LocationSelector
        v-else-if="modelSource === Purgeable.CENTRALIZED_EXCHANGES"
        v-model="modelCentralizedExchange"
        clearable
        persistent-hint
        :items="exchanges"
        :label="t('purge_selector.centralized_exchange_to_clear.label')"
        :hint="t('purge_selector.centralized_exchange_to_clear.hint')"
        data-testid="purge-cex-location"
      />
      <RuiAutoComplete
        v-if="modelSource === Purgeable.CENTRALIZED_EXCHANGES"
        v-model="modelCentralizedExchangeDataType"
        variant="outlined"
        label="Data type"
        :options="centralizedExchangePurgeTypeOptions"
        text-attr="text"
        key-attr="id"
        hide-details
        :disabled="pending"
        data-testid="purge-cex-data-type"
      />
      <LocationSelector
        v-else-if="modelSource === Purgeable.DECENTRALIZED_EXCHANGES"
        v-model="modelDecentralizedExchange"
        clearable
        persistent-hint
        :items="DECENTRALIZED_EXCHANGES"
        :label="t('purge_selector.decentralized_exchange_to_clear.label')"
        :hint="t('purge_selector.decentralized_exchange_to_clear.hint')"
      />
      <DefiModuleSelector
        v-else-if="modelSource === Purgeable.DEFI_MODULES"
        v-model="modelModule"
        :items="purgeableModules"
        :label="t('purge_selector.defi_module_to_clear.label')"
        :hint="t('purge_selector.defi_module_to_clear.hint')"
      />

      <ActionStatusIndicator
        v-if="status"
        :status="status"
      />

      <div class="flex justify-end">
        <RuiButton
          :disabled="!modelSource || pending"
          :loading="pending"
          color="error"
          data-testid="purge-submit"
          @click="showConfirmation(modelSource)"
        >
          <template #prepend>
            <RuiIcon
              name="lu-trash-2"
              size="16"
            />
          </template>

          {{ t('purge_selector.tooltip') }}
        </RuiButton>
      </div>
    </div>
  </SettingsItem>
</template>
