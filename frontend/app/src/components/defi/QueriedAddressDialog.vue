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

const { tc } = useI18n();

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
  <v-dialog
    :value="true"
    max-width="450px"
    @click:outside="close()"
    @close="close()"
  >
    <card outlined-body>
      <template #title>{{ tc('queried_address_dialog.title') }}</template>
      <template #subtitle>
        {{ tc('queried_address_dialog.subtitle', 0, { module: moduleName }) }}
      </template>
      <template #actions>
        <v-row no-gutters align="center" class="flex-nowrap">
          <v-col>
            <blockchain-account-selector
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
              :label="tc('queried_address_dialog.add')"
            />
          </v-col>
          <v-col cols="auto">
            <v-btn
              icon
              color="primary"
              :disabled="selectedAccounts.length === 0"
              @click="addAddress()"
            >
              <v-icon>mdi-plus</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </template>
      <template #details>
        <v-btn icon @click="close()">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </template>
      <div v-if="addresses.length > 0" class="queried-address-dialog__list">
        <v-row
          v-for="address in addresses"
          :key="address"
          no-gutters
          class="py-1"
        >
          <v-col>
            <labeled-address-display
              :account="getAccount(address)"
              class="queried-address-dialog__account"
            />
            <tag-display :tags="getAccount(address).tags" :small="true" />
          </v-col>
          <v-col cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <v-btn
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
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </template>
              <span>{{ tc('queried_address_dialog.remove_tooltip') }}</span>
            </v-tooltip>
          </v-col>
        </v-row>
      </div>
      <div v-else class="queried-address-dialog__empty">
        <div>
          {{
            tc('queried_address_dialog.all_address_queried', 0, {
              module: moduleName
            })
          }}
        </div>
      </div>
    </card>
  </v-dialog>
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
