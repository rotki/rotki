<script setup lang="ts">
import type { PriceOracle } from '@/modules/settings/types/price-oracle';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const open = defineModel<boolean>('open', { required: true });
const source = defineModel<PriceOracle>('source', { required: true });
const fromAsset = defineModel<string>('fromAsset', { required: true });
const toAsset = defineModel<string>('toAsset', { required: true });

const { loading = false, sourceOptions } = defineProps<{
  loading?: boolean;
  sourceOptions: { identifier: PriceOracle; label: string }[];
}>();

const emit = defineEmits<{
  confirm: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <BigDialog
    :display="open"
    :title="t('oracle_prices.cache.add')"
    :subtitle="t('oracle_prices.cache.add_subtitle')"
    :action="{ primary: t('oracle_prices.cache.dialog.create'), disabled: !fromAsset || !toAsset }"
    :layout="{ autoHeight: true, divide: true, maxWidth: '640px' }"
    :loading="loading"
    @confirm="emit('confirm')"
    @cancel="open = false"
  >
    <div class="flex flex-col gap-2">
      <RuiAutoComplete
        v-model="source"
        :label="t('oracle_prices.cache.dialog.source')"
        :options="sourceOptions"
        key-attr="identifier"
        text-attr="label"
        :disabled="loading"
        data-testid="oracle-cache-source"
      />
      <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
        <AssetSelect
          v-model="fromAsset"
          :label="t('price_management.from_asset')"
          :disabled="loading"
          data-testid="oracle-cache-from-asset"
        />
        <AssetSelect
          v-model="toAsset"
          :label="t('price_management.to_asset')"
          :disabled="loading"
          data-testid="oracle-cache-to-asset"
        />
      </div>
    </div>
  </BigDialog>
</template>
