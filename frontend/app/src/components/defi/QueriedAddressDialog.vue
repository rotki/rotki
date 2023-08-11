<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Ref } from 'vue';
import { type Module, SUPPORTED_MODULES } from '@/types/modules';

const props = defineProps<{ module: Module }>();

const emit = defineEmits<{ (e: 'close'): void }>();

const { module } = toRefs(props);

const selectedAccounts: Ref<GeneralAccount[]> = ref([]);
const ETH = Blockchain.ETH;

const store = useQueriedAddressesStore();
const { addQueriedAddress, deleteQueriedAddress } = store;
const { queriedAddresses } = storeToRefs(useQueriedAddressesStore());
const { accounts } = useAccountBalances();

const { t } = useI18n();

const moduleName = computed(() => {
  const currentModule = get(module);
  if (!currentModule) {
    return '';
  }
  const defiModule = SUPPORTED_MODULES.find(
    ({ identifier }) => identifier === currentModule
  );
  return defiModule?.name ?? currentModule;
});

const addresses = computed(() => {
  const currentModule = get(module);
  if (!currentModule) {
    return [];
  }
  const addresses = get(queriedAddresses);
  return addresses[currentModule] ?? [];
});

const usableAddresses = computed(() => {
  const currentModule = get(module);
  const accountList = get(accounts);
  const moduleAddresses = get(addresses);
  if (!currentModule || moduleAddresses.length === 0) {
    return accountList
      .filter(({ chain }) => chain === ETH)
      .map(({ address }) => address);
  }

  return accountList
    .filter(
      ({ chain, address }) =>
        chain === ETH && !moduleAddresses.includes(address)
    )
    .map(({ address }) => address);
});

const addAddress = async function () {
  const currentModule = get(module);
  const currentAccount = get(selectedAccounts);
  assert(currentModule && currentAccount.length > 0);
  await addQueriedAddress({
    module: currentModule,
    address: currentAccount[0].address
  });
  set(selectedAccounts, []);
};

const getAccount = (address: string): GeneralAccount => {
  const account = get(accounts).find(value => value.address === address);
  assert(account);
  return account;
};

const close = () => {
  set(selectedAccounts, []);
  emit('close');
};
</script>

<template>
  <VDialog
    :value="true"
    max-width="450px"
    @click:outside="close()"
    @close="close()"
  >
    <Card>
      <template #title>{{ t('queried_address_dialog.title') }}</template>
      <template #subtitle>
        {{ t('queried_address_dialog.subtitle', { module: moduleName }) }}
      </template>
      <template #actions>
        <VRow no-gutters align="center" class="flex-nowrap">
          <VCol>
            <BlockchainAccountSelector
              v-model="selectedAccounts"
              outlined
              flat
              dense
              no-padding
              hide-on-empty-usable
              max-width="340px"
              :usable-addresses="usableAddresses"
              class="queried-address-dialog__selector"
              :chains="[ETH]"
              :label="t('queried_address_dialog.add')"
            />
          </VCol>
          <VCol cols="auto">
            <VBtn
              icon
              color="primary"
              :disabled="selectedAccounts.length === 0"
              @click="addAddress()"
            >
              <VIcon>mdi-plus</VIcon>
            </VBtn>
          </VCol>
        </VRow>
      </template>
      <template #details>
        <VBtn icon @click="close()">
          <VIcon>mdi-close</VIcon>
        </VBtn>
      </template>
      <div v-if="addresses.length > 0" class="queried-address-dialog__list">
        <VRow
          v-for="address in addresses"
          :key="address"
          no-gutters
          class="py-1"
        >
          <VCol>
            <LabeledAddressDisplay
              :account="getAccount(address)"
              class="queried-address-dialog__account"
            />
            <TagDisplay :tags="getAccount(address).tags" :small="true" />
          </VCol>
          <VCol cols="auto">
            <VTooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <VBtn
                  small
                  icon
                  color="primary"
                  v-bind="attrs"
                  v-on="on"
                  @click="
                    deleteQueriedAddress({
                      module,
                      address
                    })
                  "
                >
                  <VIcon>mdi-delete</VIcon>
                </VBtn>
              </template>
              <span>{{ t('queried_address_dialog.remove_tooltip') }}</span>
            </VTooltip>
          </VCol>
        </VRow>
      </div>
      <div v-else class="queried-address-dialog__empty">
        <div>
          {{
            t('queried_address_dialog.all_address_queried', {
              module: moduleName
            })
          }}
        </div>
      </div>
    </Card>
  </VDialog>
</template>

<style scoped lang="scss">
.queried-address-dialog {
  &__list {
    overflow-y: scroll;
    overflow-x: hidden;
    width: 99%;
    padding: 8px;
    height: 250px;
  }

  &__empty {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 250px;
  }

  &__account {
    width: 300px;
  }
}

:deep(.labeled-address-display) {
  .labeled-address-display {
    &__chip {
      max-width: 241px;
    }
  }
}
</style>
