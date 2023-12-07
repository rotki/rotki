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
    <RuiCard>
      <template #custom-header>
        <div class="flex items-start justify-between p-4">
          <div>
            <h5 class="text-h5">
              {{ t('queried_address_dialog.title') }}
            </h5>
            <div class="text-rui-text-secondary text-body-2">
              {{ t('queried_address_dialog.subtitle', { module: moduleName }) }}
            </div>
          </div>

          <RuiButton class="shrink-0" variant="text" icon @click="close()">
            <RuiIcon name="close-line" />
          </RuiButton>
        </div>
      </template>
      <div class="flex items-center gap-2">
        <BlockchainAccountSelector
          v-model="selectedAccounts"
          outlined
          flat
          dense
          no-padding
          hide-on-empty-usable
          max-width="340px"
          :usable-addresses="usableAddresses"
          class="queried-address-dialog__selector flex-1"
          :chains="[ETH]"
          :label="t('queried_address_dialog.add')"
        />
        <RuiButton
          :disabled="selectedAccounts.length === 0"
          variant="text"
          icon
          @click="addAddress()"
        >
          <RuiIcon name="add-line" />
        </RuiButton>
      </div>
      <div v-if="addresses.length > 0" class="overflow-y-scroll mt-4 h-[16rem]">
        <div
          v-for="address in addresses"
          :key="address"
          class="flex items-start gap-4 py-2 border-t border-default"
        >
          <div class="flex-1">
            <LabeledAddressDisplay :account="getAccount(address)" />
            <TagDisplay :tags="getAccount(address).tags" :small="true" />
          </div>
          <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
            <template #activator>
              <RuiButton
                variant="text"
                icon
                color="primary"
                class="!p-2 mt-0.5"
                @click="
                  deleteQueriedAddress({
                    module,
                    address
                  })
                "
              >
                <RuiIcon size="16" name="delete-bin-line" />
              </RuiButton>
            </template>
            <span>{{ t('queried_address_dialog.remove_tooltip') }}</span>
          </RuiTooltip>
        </div>
      </div>
      <div
        v-else
        class="border-t mt-4 pt-4 text-body-2 text-center text-rui-text-secondary h-[16rem]"
      >
        {{
          t('queried_address_dialog.all_address_queried', {
            module: moduleName
          })
        }}
      </div>
    </RuiCard>
  </VDialog>
</template>
