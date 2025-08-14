<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import { isEvmNativeToken } from '@/types/asset';

const props = defineProps<{
  row: AssetBalanceWithPrice;
}>();

const { t } = useI18n({ useScope: 'global' });

const tab = ref(0);

const hasPerProtocol = computed<boolean>(() => {
  const perProtocol = props.row.perProtocol;
  return (perProtocol && perProtocol.length > 1) ?? false;
});

const hasBreakdown = computed<boolean>(() => {
  const breakdown = props.row.breakdown;
  const isNativeToken = isEvmNativeToken(props.row.asset);
  const hasBreakdown = breakdown && breakdown.length > 0;
  return ((hasBreakdown && !isNativeToken) || (isNativeToken && hasBreakdown && !get(hasPerProtocol))) ?? false;
});

const showTabs = logicAnd(hasBreakdown, hasPerProtocol);
</script>

<template>
  <div class="rounded-xl my-2">
    <template v-if="showTabs">
      <RuiTabs
        v-model="tab"
        color="primary"
        class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-3"
      >
        <RuiTab>{{ t('asset_details_layout.tab.breakdown') }}</RuiTab>
        <RuiTab>{{ t('asset_details_layout.tab.per_location') }}</RuiTab>
      </RuiTabs>
      <RuiTabItems :model-value="tab">
        <RuiTabItem>
          <div class="bg-white dark:bg-[#1E1E1E] rounded-xl p-4">
            <slot name="breakdown" />
          </div>
        </RuiTabItem>
        <RuiTabItem>
          <div class="bg-white dark:bg-[#1E1E1E] rounded-xl p-4">
            <slot name="perprotocol" />
          </div>
        </RuiTabItem>
      </RuiTabItems>
    </template>

    <!-- Single rounded div when only one slot is available -->
    <template v-else>
      <div class="bg-white dark:bg-[#1E1E1E] rounded-xl p-4">
        <slot
          v-if="hasBreakdown"
          name="breakdown"
        />
        <slot
          v-else-if="hasPerProtocol"
          name="perprotocol"
        />
      </div>
    </template>
  </div>
</template>
