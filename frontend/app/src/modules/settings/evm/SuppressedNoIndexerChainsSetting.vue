<script setup lang="ts">
import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import SettingMultiSelect from '@/modules/settings/controls/SettingMultiSelect.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const { t } = useI18n({ useScope: 'global' });
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
    data-testid="suppressed-no-indexer-chains-setting"
  >
    <template #title>
      {{ t('evm_settings.indexer.suppressed_no_indexer_chains.title') }}
    </template>
    <template #subtitle>
      {{ t('evm_settings.indexer.suppressed_no_indexer_chains.subtitle') }}
    </template>
    <SettingMultiSelect
      setting="suppressNoIndexerChains"
      :options="txEvmChains"
      key-attr="id"
      text-attr="name"
      :label="t('evm_settings.indexer.suppressed_no_indexer_chains.label')"
      :hint="t('evm_settings.indexer.suppressed_no_indexer_chains.hint')"
      data-testid="suppressed-no-indexer-chains"
      :item-height="48"
      :success-message="t('evm_settings.indexer.suppressed_no_indexer_chains.success')"
      :error-message="t('evm_settings.indexer.suppressed_no_indexer_chains.error')"
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
    </SettingMultiSelect>
  </SettingsItem>
</template>
