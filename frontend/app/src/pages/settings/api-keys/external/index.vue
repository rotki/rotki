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
      t('navigation_menu.api_keys_sub.external_services'),
    ]"
  >
    <template #buttons>
      <HintMenuIcon>
        {{ t('external_services.subtitle') }}
      </HintMenuIcon>
    </template>

    <EtherscanApiKeys />
    <BlockscoutApiKey />
    <CryptoCompareApiKey />
    <BeaconchainApiKey />
    <CovalentApiKey />
    <LoopringApiKey />
    <OpenSeaApiKey />
    <MoneriumAuth />
    <TheGraphApiKey />
  </TablePageLayout>
</template>
