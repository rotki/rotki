<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

function removeIdentifierParam(): void {
  const query = { ...route.query };
  delete query.identifiers;
  router.push({ query });
}

function removeEventIdentifierParam(): void {
  const query = { ...route.query };
  delete query.eventIdentifiers;
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
    v-if="route.query.eventIdentifiers"
    class="mb-4"
  >
    <RuiChip
      closeable
      color="primary"
      size="sm"
      variant="outlined"
      @click:close="removeEventIdentifierParam()"
    >
      {{ t('transactions.events.show_negative_balance') }}
    </RuiChip>
  </div>
</template>
