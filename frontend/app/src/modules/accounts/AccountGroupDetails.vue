<script setup lang="ts">
const tab = defineModel<number>({ required: true });

defineProps<{
  isXpub: boolean;
}>();

defineSlots<{
  'per-chain': () => any;
  'aggregated': () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <!-- the expanded cell insets its content evenly, so the content carries no outer margin -->
  <div v-if="isXpub">
    <slot name="per-chain" />
  </div>
  <div v-else>
    <RuiTabs
      v-model="tab"
      color="primary"
      variant="segmented"
      class="mb-4"
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
