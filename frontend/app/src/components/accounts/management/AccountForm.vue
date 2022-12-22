<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import Fragment from '@/components/helper/Fragment';
import AccountSelector from '@/components/accounts/management/inputs/AccountSelector.vue';
import { InputMode } from '@/types/input-mode';
import MetamaskAccountForm from '@/components/accounts/management/types/MetamaskAccountForm.vue';
import ValidatorAccountForm from '@/components/accounts/management/types/ValidatorAccountForm.vue';
import XpubAccountForm from '@/components/accounts/management/types/XpubAccountForm.vue';
import AddressAccountForm from '@/components/accounts/management/types/AddressAccountForm.vue';
import { isBtcChain } from '@/types/blockchain/chains';

const props = defineProps<{ context: Blockchain }>();

const { context } = toRefs(props);

const blockchain = ref<Blockchain>(Blockchain.ETH);
const inputMode = ref<InputMode>(InputMode.MANUAL_ADD);

const { accountToEdit } = useAccountDialog();

onMounted(() => {
  const account = get(accountToEdit);
  if (account) {
    set(blockchain, account.chain);
    if ('xpub' in account) {
      set(inputMode, InputMode.XPUB_ADD);
    }
  }
});

watch(context, ctx => {
  if (!get(accountToEdit)) {
    set(blockchain, ctx);
  }
});
</script>

<template>
  <fragment>
    <account-selector
      :input-mode="inputMode"
      :blockchain="blockchain"
      @update:blockchain="blockchain = $event"
      @update:input-mode="inputMode = $event"
    />
    <metamask-account-form v-if="inputMode === InputMode.METAMASK_IMPORT" />
    <validator-account-form v-else-if="blockchain === Blockchain.ETH2" />
    <xpub-account-form
      v-else-if="isBtcChain(blockchain) && inputMode === InputMode.XPUB_ADD"
      :blockchain="blockchain"
    />
    <address-account-form v-else :blockchain="blockchain" />
  </fragment>
</template>
