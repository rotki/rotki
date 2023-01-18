<script lang="ts" setup>
import { Blockchain } from '@rotki/common/lib/blockchain';

const chain = Blockchain.OPTIMISM;
</script>

<template>
  <evm-rpc-node-manager :chain="chain" />
</template>
