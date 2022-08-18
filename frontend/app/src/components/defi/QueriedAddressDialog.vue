<template>
  <v-dialog
    v-if="!!module"
    max-width="450px"
    :value="!!module"
    @click:outside="close"
    @close="close"
  >
    <card outlined-body>
      <template #title>{{ $t('queried_address_dialog.title') }}</template>
      <template #subtitle>
        {{ $t('queried_address_dialog.subtitle', { module: moduleName }) }}
      </template>
      <template #actions>
        <v-row no-gutters align="center" class="flex-nowrap">
          <v-col>
            <blockchain-account-selector
              v-model="account"
              outlined
              flat
              dense
              no-padding
              hide-on-empty-usable
              max-width="340px"
              :usable-addresses="usableAddresses"
              class="queried-address-dialog__selector"
              :chains="[ETH]"
              :label="$t('queried_address_dialog.add')"
            />
          </v-col>
          <v-col cols="auto">
            <v-btn
              icon
              color="primary"
              :disabled="account === null"
              @click="addAddress"
            >
              <v-icon>mdi-plus</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </template>
      <template #details>
        <v-btn icon @click="close">
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
              <span>{{ $t('queried_address_dialog.remove_tooltip') }}</span>
            </v-tooltip>
          </v-col>
        </v-row>
      </div>
      <div v-else class="queried-address-dialog__empty">
        <div>
          {{
            $t('queried_address_dialog.all_address_queried', {
              module: moduleName
            })
          }}
        </div>
      </div>
    </card>
  </v-dialog>
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs
} from '@vue/composition-api';
import { set, get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { SUPPORTED_MODULES } from '@/components/defi/wizard/consts';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { Nullable } from '@/types';
import { Module } from '@/types/modules';
import { assert } from '@/utils/assertions';

export default defineComponent({
  name: 'QueriedAddressDialog',
  components: { TagDisplay, LabeledAddressDisplay },
  props: {
    module: {
      required: false,
      type: String as PropType<Nullable<Module>>,
      default: null
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const { module } = toRefs(props);

    const account: Ref<Nullable<GeneralAccount>> = ref(null);
    const ETH = Blockchain.ETH;

    const store = useQueriedAddressesStore();
    const { addQueriedAddress, deleteQueriedAddress } = store;
    let { queriedAddresses } = storeToRefs(useQueriedAddressesStore());
    const { accounts } = storeToRefs(useBlockchainAccountsStore());

    const moduleName = computed(() => {
      let currentModule = get(module);
      if (!currentModule) {
        return '';
      }
      const defiModule = SUPPORTED_MODULES.find(
        ({ identifier }) => identifier === currentModule
      );
      return defiModule?.name ?? currentModule;
    });

    const addresses = computed(() => {
      let currentModule = get(module);
      if (!currentModule) {
        return [];
      }
      const addresses = get(queriedAddresses);
      return addresses[currentModule] ?? [];
    });

    const usableAddresses = computed(() => {
      let currentModule = get(module);
      let accountList = get(accounts);
      let moduleAddresses = get(addresses);
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
      const currentAccount = get(account);
      assert(currentModule && currentAccount);
      await addQueriedAddress({
        module: currentModule,
        address: currentAccount.address
      });
      set(account, null);
    };

    const getAccount = (address: string): GeneralAccount | undefined => {
      return get(accounts).find(value => value.address === address);
    };

    const close = () => {
      set(account, null);
      emit('close');
    };

    return {
      ETH,
      account,
      accounts,
      addresses,
      queriedAddresses,
      usableAddresses,
      moduleName,
      addAddress,
      getAccount,
      deleteQueriedAddress,
      close
    };
  }
});
</script>

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

::v-deep {
  .labeled-address-display {
    &__chip {
      max-width: 241px;
    }
  }
}
</style>
