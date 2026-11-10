<script setup lang="ts">
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { DECENTRALIZED_EXCHANGES } from '@/modules/core/common/modules';
import { Purgeable } from '@/modules/session/purge';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { usePurgeData } from '@/modules/settings/data-security/data-management/use-purge-data';
import DefiModuleSelector from '@/modules/settings/modules/DefiModuleSelector.vue';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import ActionStatusIndicator from '@/modules/shell/components/error/ActionStatusIndicator.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  centralizedExchangePurgeTypeOptions,
  chainsSelection,
  csvImportLocations,
  exchanges,
  modelCentralizedExchange,
  modelCentralizedExchangeDataType,
  modelCsvImportLocation,
  modelChain,
  modelDecentralizedExchange,
  modelModule,
  modelSource,
  pending,
  purge,
  purgeable,
  purgeableModules,
  purgeQuestion,
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
        :label="t('purge_selector.label')"
        :options="purgeable"
        text-attr="text"
        key-attr="id"
        details="hidden"
        :disabled="pending"
        data-testid="purge-source"
      />
      <ChainSelect
        v-if="modelSource === Purgeable.TRANSACTIONS"
        :model-value="modelChain"
        clearable
        :items="chainsSelection"
        :label="t('purge_selector.chain_to_clear.label')"
        :hint="t('purge_selector.chain_to_clear.hint')"
        @update:model-value="modelChain = $event ?? ''"
      />
      <LocationSelector
        v-else-if="modelSource === Purgeable.CSV_IMPORTS"
        v-model="modelCsvImportLocation"
        clearable
        :items="csvImportLocations"
        :label="t('purge_selector.csv_import_location_to_clear.label')"
        :hint="t('purge_selector.csv_import_location_to_clear.hint')"
        data-testid="purge-csv-location"
      />
      <LocationSelector
        v-else-if="modelSource === Purgeable.CENTRALIZED_EXCHANGES"
        v-model="modelCentralizedExchange"
        clearable
        :items="exchanges"
        :label="t('purge_selector.centralized_exchange_to_clear.label')"
        :hint="t('purge_selector.centralized_exchange_to_clear.hint')"
        data-testid="purge-cex-location"
      />
      <RuiAutoComplete
        v-if="modelSource === Purgeable.CENTRALIZED_EXCHANGES"
        v-model="modelCentralizedExchangeDataType"
        label="Data type"
        :options="centralizedExchangePurgeTypeOptions"
        text-attr="text"
        key-attr="id"
        details="hidden"
        :disabled="pending"
        data-testid="purge-cex-data-type"
      />
      <LocationSelector
        v-else-if="modelSource === Purgeable.DECENTRALIZED_EXCHANGES"
        v-model="modelDecentralizedExchange"
        clearable
        :items="DECENTRALIZED_EXCHANGES"
        :label="t('purge_selector.decentralized_exchange_to_clear.label')"
        :hint="t('purge_selector.decentralized_exchange_to_clear.hint')"
      />
      <DefiModuleSelector
        v-else-if="modelSource === Purgeable.DEFI_MODULES"
        :model-value="modelModule"
        :items="purgeableModules"
        :label="t('purge_selector.defi_module_to_clear.label')"
        :hint="t('purge_selector.defi_module_to_clear.hint')"
        @update:model-value="modelModule = $event ?? ''"
      />

      <ActionStatusIndicator
        v-if="status"
        :status="status"
      />

      <div class="flex">
        <ConfirmPopover
          :question="purgeQuestion"
          @confirm="purge(modelSource)"
        >
          <template #activator="{ attrs }">
            <RuiButton
              :disabled="!modelSource || pending"
              :loading="pending"
              variant="outlined"
              color="error"
              data-testid="purge-submit"
              v-bind="attrs"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-trash-2"
                  size="16"
                />
              </template>

              {{ t('purge_selector.tooltip') }}
            </RuiButton>
          </template>
        </ConfirmPopover>
      </div>
    </div>
  </SettingsItem>
</template>
