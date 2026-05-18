<script setup lang="ts">
import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { t } = useI18n({ useScope: 'global' });
const { suppressNoIndexerChains } = storeToRefs(useFrontendSettingsStore());
const { txEvmChains } = useSupportedChains();

const [DefineChainItem, ReuseChainItem] = createReusableTemplate<{ item: EvmChainInfo; size: string }>();
</script>

<template>
  <DefineChainItem #default="{ item, size }">
    <div class="flex items-center gap-2">
      <ChainIcon
        :chain="item.id"
        :size="size"
      />
      <span>{{ item.name }}</span>
    </div>
  </DefineChainItem>

  <SettingsItem
    :id="SettingsHighlightIds.SUPPRESSED_NO_INDEXER_CHAINS"
    data-cy="suppressed-no-indexer-chains-setting"
  >
    <template #title>
      {{ t('evm_settings.indexer.suppressed_no_indexer_chains.title') }}
    </template>
    <template #subtitle>
      {{ t('evm_settings.indexer.suppressed_no_indexer_chains.subtitle') }}
    </template>
    <SettingsOption
      #default="{ error, success, updateImmediate }"
      frontend-setting
      setting="suppressNoIndexerChains"
      :error-message="t('evm_settings.indexer.suppressed_no_indexer_chains.error')"
      :success-message="t('evm_settings.indexer.suppressed_no_indexer_chains.success')"
    >
      <RuiAutoComplete
        :options="txEvmChains"
        :label="t('evm_settings.indexer.suppressed_no_indexer_chains.label')"
        :model-value="suppressNoIndexerChains"
        :success-messages="success"
        :error-messages="error"
        :hint="t('evm_settings.indexer.suppressed_no_indexer_chains.hint')"
        data-cy="suppressed-no-indexer-chains"
        variant="outlined"
        key-attr="id"
        text-attr="name"
        chips
        :item-height="48"
        auto-select-first
        @update:model-value="updateImmediate($event)"
      >
        <template #selection="{ item }">
          <ReuseChainItem
            :item="item"
            size="20px"
          />
        </template>
        <template #item="{ item }">
          <ReuseChainItem
            :item="item"
            size="24px"
          />
        </template>
      </RuiAutoComplete>
    </SettingsOption>
  </SettingsItem>
</template>
