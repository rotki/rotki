<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

function removeIdentifierParam(): void {
  const query = { ...route.query };
  delete query.identifiers;
  router.push({ query });
}

function removeGroupIdentifierParam(): void {
  const query = { ...route.query };
  delete query.groupIdentifiers;
  delete query.highlightIdentifier;
  router.push({ query });
}
</script>

<template>
  <div
    v-if="route.query.identifiers"
    class="mb-4"
  >
    <RuiChip
      closeable
      color="primary"
      size="sm"
      variant="outlined"
      @click:close="removeIdentifierParam()"
    >
      {{ t('transactions.events.show_missing_acquisition') }}
    </RuiChip>
  </div>

  <div
    v-if="route.query.groupIdentifiers"
    class="mb-4"
  >
    <RuiTooltip
      :popper="{ placement: 'bottom' }"
      :open-delay="400"
      tooltip-class="max-w-80"
    >
      <template #activator>
        <RuiChip
          closeable
          color="primary"
          size="sm"
          variant="outlined"
          @click:close="removeGroupIdentifierParam()"
        >
          {{ t('transactions.events.show_negative_balance') }}
        </RuiChip>
      </template>
      {{ t('historical_balances.negative_balances.view_event_tooltip') }}
    </RuiTooltip>
  </div>
</template>
