<script setup lang="ts">
import AccountFormApiKeyAlertContent from '@/modules/accounts/management/AccountFormApiKeyAlertContent.vue';

const { service } = defineProps<{
  service: 'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc';
}>();

const type = computed<'warning' | 'info'>(() => service === 'beaconchain' ? 'info' : 'warning');
</script>

<template>
  <RuiAlert
    :type="type"
    class="mb-6 -mt-2"
  >
    <AccountFormApiKeyAlertContent :service="service" />
  </RuiAlert>
</template>
