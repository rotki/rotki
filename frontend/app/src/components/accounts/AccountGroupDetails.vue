<script setup lang="ts">
const tab = defineModel<number>({ required: true });

defineProps<{
  isXpub: boolean;
}>();

defineSlots<{
  'per-chain': () => any;
  'aggregated': () => any;
}>();

const { t } = useI18n();
</script>

<template>
  <div
    v-if="isXpub"
    class="my-2"
  >
    <slot name="per-chain" />
  </div>
  <div
    v-else
    class="rounded-xl my-2"
  >
    <RuiTabs
      v-model="tab"
      color="primary"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-3"
    >
      <RuiTab>{{ t('account_balances.aggregated_assets') }}</RuiTab>
      <RuiTab>{{ t('account_balances.per_chain') }}</RuiTab>
    </RuiTabs>
    <RuiTabItems :model-value="tab">
      <RuiTabItem>
        <slot name="aggregated" />
      </RuiTabItem>
      <RuiTabItem>
        <slot name="per-chain" />
      </RuiTabItem>
    </RuiTabItems>
  </div>
</template>
