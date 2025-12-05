<script setup lang="ts">
import AccountFormApiKeyAlertContent from '@/components/accounts/management/AccountFormApiKeyAlertContent.vue';

defineProps<{
  service: 'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc';
}>();
</script>

<template>
  <RuiAlert
    type="warning"
    class="mb-6 -mt-2"
  >
    <AccountFormApiKeyAlertContent :service="service" />
  </RuiAlert>
</template>
