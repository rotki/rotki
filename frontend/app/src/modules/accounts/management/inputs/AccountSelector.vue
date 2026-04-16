<script setup lang="ts">
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import { useAccountLoading } from '@/modules/accounts/use-account-loading';

const chain = defineModel<string | undefined>('chain', { required: true });

defineProps<{
  editMode: boolean;
  chainIds: string[];
}>();

const { loading } = useAccountLoading();
</script>

<template>
  <ChainSelect
    v-model="chain"
    :disabled="loading || editMode"
    :items="chainIds"
  />
</template>
