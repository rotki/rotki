<template>
  <non-fungible-balances />
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import NonFungibleBalances from '@/components/accounts/balances/NonFungibleBalances.vue';

export default defineComponent({
  name: 'NonFungibleBalancePage',
  components: { NonFungibleBalances }
});
</script>
