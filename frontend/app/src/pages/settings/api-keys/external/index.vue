<script setup lang="ts">
const { t } = useI18n();
const { load } = useExternalApiKeys(t);

onMounted(async () => {
  await load();
});
</script>

<template>
  <TablePageLayout
    data-cy="external-keys"
    :title="[
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.external_services')
    ]"
  >
    <template #buttons>
      <HintMenuIcon max-width="25rem">
        {{ t('external_services.subtitle') }}
      </HintMenuIcon>
    </template>

    <EtherscanApiKeys />
    <CryptoCompareApiKey />
    <BeaconchainApiKey />
    <CovalentApiKey />
    <LoopringApiKey />
    <OpenSeaApiKey />
  </TablePageLayout>
</template>
