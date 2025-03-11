<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { CamelCase } from '@/types/common';
import AppImage from '@/components/common/AppImage.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import LabeledAddressDisplay from '@/components/display/LabeledAddressDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import TagDisplay from '@/components/tags/TagDisplay.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useBlockchainStore } from '@/store/blockchain';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { type Module, SUPPORTED_MODULES } from '@/types/modules';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { assert, Blockchain, transformCase } from '@rotki/common';

const props = defineProps<{ module: Module }>();

const emit = defineEmits<{ (e: 'close'): void }>();

const { module } = toRefs(props);

const selectedAccounts = ref<BlockchainAccount<AddressData>[]>([]);
const ETH = Blockchain.ETH;

const store = useQueriedAddressesStore();
const { addQueriedAddress, deleteQueriedAddress } = store;
const { queriedAddresses } = storeToRefs(useQueriedAddressesStore());
const { getAccounts, getAddresses } = useBlockchainStore();

const { t } = useI18n();

const accounts = computed<BlockchainAccount[]>(() => getAccounts(ETH));

const currentModule = computed(() => {
  const currentModule = get(module);
  if (!currentModule)
    return undefined;

  return SUPPORTED_MODULES.find(({ identifier }) => identifier === currentModule);
});

const moduleName = useRefMap(currentModule, m => m?.name);
const moduleIcon = useRefMap(currentModule, m => m?.icon);

const addresses = computed(() => {
  const currentModule = get(module);
  if (!currentModule)
    return [];

  const addresses = get(queriedAddresses);
  const index = transformCase(currentModule, true) as CamelCase<Module>;
  return addresses[index] ?? [];
});

const usableAddresses = computed(() => {
  const currentModule = get(module);
  const accountList = getAddresses(Blockchain.ETH);
  const moduleAddresses = get(addresses);
  if (!currentModule || moduleAddresses.length === 0)
    return accountList;

  return accountList.filter(address => !moduleAddresses.includes(address));
});

async function addAddress() {
  const currentModule = get(module);
  const currentAccount = get(selectedAccounts);
  assert(currentModule && currentAccount.length > 0);
  await addQueriedAddress({
    address: getAccountAddress(currentAccount[0]),
    module: currentModule,
  });
  set(selectedAccounts, []);
}

function getAccount(address: string): BlockchainAccount {
  const account = get(accounts).find(account => getAccountAddress(account) === address);
  assert(account);
  return account;
}

function close() {
  set(selectedAccounts, []);
  emit('close');
}
</script>

<template>
  <RuiDialog
    :model-value="true"
    max-width="450px"
    @closed="close()"
  >
    <RuiCard>
      <template #custom-header>
        <div class="flex items-center justify-between p-4 gap-4">
          <AdaptiveWrapper>
            <AppImage
              size="24px"
              contain
              :src="moduleIcon"
            />
          </AdaptiveWrapper>
          <RuiCardHeader class="p-0">
            <template #header>
              {{ t('queried_address_dialog.title') }}
            </template>
            <template #subheader>
              {{ t('queried_address_dialog.subtitle', { module: moduleName }) }}
            </template>
          </RuiCardHeader>

          <RuiButton
            class="shrink-0"
            variant="text"
            icon
            @click="close()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </template>
      <div class="flex items-center gap-2">
        <BlockchainAccountSelector
          v-model="selectedAccounts"
          outlined
          dense
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
          <RuiIcon name="lu-plus" />
        </RuiButton>
      </div>
      <div
        v-if="addresses.length > 0"
        class="overflow-y-scroll mt-4 h-[16rem]"
      >
        <div
          v-for="address in addresses"
          :key="address"
          class="flex items-start gap-4 py-2 border-t border-default"
        >
          <div class="flex-1">
            <LabeledAddressDisplay :account="getAccount(address)" />
            <TagDisplay
              :tags="getAccount(address).tags"
              small
            />
          </div>
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                variant="text"
                icon
                color="primary"
                class="!p-2 mt-0.5"
                @click="
                  deleteQueriedAddress({
                    module,
                    address,
                  })
                "
              >
                <RuiIcon
                  size="16"
                  name="lu-trash-2"
                />
              </RuiButton>
            </template>

            {{ t('queried_address_dialog.remove_tooltip') }}
          </RuiTooltip>
        </div>
      </div>
      <div
        v-else
        class="border-t border-default mt-4 pt-4 text-body-2 text-center text-rui-text-secondary h-[16rem]"
      >
        {{
          t('queried_address_dialog.all_address_queried', {
            module: moduleName,
          })
        }}
      </div>
    </RuiCard>
  </RuiDialog>
</template>
