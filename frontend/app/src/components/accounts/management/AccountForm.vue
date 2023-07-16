<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { InputMode } from '@/types/input-mode';
import { isBtcChain } from '@/types/blockchain/chains';

const props = defineProps<{ context: Blockchain }>();

const { context } = toRefs(props);

const blockchain = ref<Blockchain>(Blockchain.ETH);
const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);
const allEvmChains = ref(true);

const { accountToEdit } = useAccountDialog();

onMounted(() => {
  const account = get(accountToEdit);
  if (account) {
    set(blockchain, account.chain);
    if ('xpub' in account) {
      set(inputMode, InputMode.XPUB_ADD);
    }
  } else {
    set(blockchain, get(context));
  }
});

watch(context, ctx => {
  if (!get(accountToEdit)) {
    set(blockchain, ctx);
  }
});
</script>

<template>
  <div class="pt-2">
    <AccountSelector
      :input-mode="inputMode"
      :blockchain="blockchain"
      @update:blockchain="blockchain = $event"
      @update:input-mode="inputMode = $event"
    />
    <MetamaskAccountForm
      v-if="inputMode === InputMode.METAMASK_IMPORT"
      :blockchain="blockchain"
      :all-evm-chains="allEvmChains"
    >
      <template #selector="{ loading }">
        <AllEvmChainsSelector v-model="allEvmChains" :disabled="loading" />
      </template>
    </MetamaskAccountForm>
    <ValidatorAccountForm v-else-if="blockchain === Blockchain.ETH2" />
    <XpubAccountForm
      v-else-if="isBtcChain(blockchain) && inputMode === InputMode.XPUB_ADD"
      :blockchain="blockchain"
    />
    <AddressAccountForm
      v-else
      :blockchain="blockchain"
      :all-evm-chains="allEvmChains"
    >
      <template #selector="{ loading }">
        <AllEvmChainsSelector v-model="allEvmChains" :disabled="loading" />
      </template>
    </AddressAccountForm>
  </div>
</template>
