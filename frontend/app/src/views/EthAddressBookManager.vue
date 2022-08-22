<template>
  <eth-address-book-management />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import EthAddressBookManagement from '@/components/eth-address-book-manager/EthAddressBookManagement.vue';

export default defineComponent({
  name: 'EthAddressBookManager',
  components: { EthAddressBookManagement }
});
</script>
