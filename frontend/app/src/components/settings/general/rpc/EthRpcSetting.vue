<script lang="ts" setup>
import { Blockchain } from '@rotki/common/lib/blockchain';

const chain = Blockchain.ETH;
</script>

<template>
  <evm-rpc-node-manager :chain="chain" />
</template>
