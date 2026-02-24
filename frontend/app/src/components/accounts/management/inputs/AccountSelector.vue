<script setup lang="ts">
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import { useAccountLoading } from '@/composables/accounts/loading';

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
