<script setup lang="ts">
import type { AddressAccount, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { assert, Blockchain, transformCase } from '@rotki/common';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useQueriedAddressOperations } from '@/modules/accounts/use-queried-address-operations';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { type Module, SUPPORTED_MODULES } from '@/modules/core/common/modules';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import LabeledAddressDisplay from '@/modules/shell/components/display/LabeledAddressDisplay.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import IconMark from '@/modules/shell/components/IconMark.vue';
import TagDisplay from '@/modules/tags/TagDisplay.vue';

interface QueriedAddressRow {
  address: string;
  /**
   * The tracked account behind the address. Removing an account leaves its queried addresses in
   * place, so an address can outlive its account; it then shows bare, still removable.
   */
  account: BlockchainAccount | undefined;
}

const { module } = defineProps<{ module: Module }>();

const emit = defineEmits<{ close: [] }>();

const selectedAccounts = ref<AddressAccount[]>([]);
const ETH = Blockchain.ETH;

const { addQueriedAddress, deleteQueriedAddress } = useQueriedAddressOperations();
const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
const { getAccounts } = useBlockchainAccountsStore();
const { getAddresses } = useAccountAddresses();

const { t } = useI18n({ useScope: 'global' });

const accounts = computed<BlockchainAccount[]>(() => getAccounts(ETH));

const currentModule = computed(() => {
  if (!module)
    return undefined;

  return SUPPORTED_MODULES.find(({ identifier }) => identifier === module);
});

const addresses = computed<string[]>(() => {
  if (!module)
    return [];

  const addresses = get(queriedAddresses);
  const index = transformCase(module, true);
  return addresses[index] ?? [];
});

const rows = computed<QueriedAddressRow[]>(() => get(addresses).map(address => ({
  account: get(accounts).find(account => getAccountAddress(account) === address),
  address,
})));

const usableAddresses = computed(() => {
  const accountList = getAddresses(Blockchain.ETH);
  const moduleAddresses = get(addresses);
  if (!module || moduleAddresses.length === 0)
    return accountList;

  return accountList.filter(address => !moduleAddresses.includes(address));
});

async function addAddress() {
  const currentAccount = get(selectedAccounts);
  assert(module && currentAccount.length > 0);
  await addQueriedAddress({
    address: getAccountAddress(currentAccount[0]),
    module,
  });
  set(selectedAccounts, []);
}

function close() {
  set(selectedAccounts, []);
  emit('close');
}
</script>

<template>
  <RuiDialog
    model-value
    max-width="520px"
    @closed="close()"
  >
    <RuiCard>
      <template #custom-header>
        <div class="flex items-start gap-3 p-4 pb-2">
          <IconMark
            size="1.25rem"
            class="mt-0.5 shrink-0"
            :src="currentModule?.icon"
          />
          <div class="flex-1 min-w-0">
            <div class="text-base font-medium text-rui-text">
              {{ t('queried_address_dialog.title') }}
            </div>
            <div class="text-sm text-rui-text-secondary">
              {{ t('queried_address_dialog.subtitle', { module: currentModule?.name }) }}
            </div>
          </div>
          <RuiButton
            class="shrink-0 -mt-1 -mr-2"
            variant="text"
            size="sm"
            icon
            :aria-label="t('common.actions.close')"
            data-testid="queried-address-close"
            @click="close()"
          >
            <RuiIcon
              name="lu-x"
              size="18"
            />
          </RuiButton>
        </div>
      </template>
      <div class="flex items-end gap-2">
        <BlockchainAccountSelector
          v-model="selectedAccounts"
          class="flex-1 min-w-0"
          :source="{ chains: [ETH], hideOnEmptyUsable: true, usableAddresses }"
          :field="{ dense: true, label: t('queried_address_dialog.add') }"
        />
        <RuiButton
          :disabled="selectedAccounts.length === 0"
          class="h-8"
          size="sm"
          variant="outlined"
          color="primary"
          data-testid="queried-address-add"
          @click="addAddress()"
        >
          {{ t('common.actions.add') }}
        </RuiButton>
      </div>
      <div
        v-if="rows.length > 0"
        class="overflow-y-auto mt-2 max-h-72 rounded-rui-control border border-rui-divider between:border-t between:border-rui-divider"
      >
        <div
          v-for="row in rows"
          :key="row.address"
          class="flex items-center gap-3 px-3 py-2"
          data-testid="queried-address-row"
        >
          <div class="flex-1 min-w-0">
            <template v-if="row.account">
              <LabeledAddressDisplay :account="row.account" />
              <TagDisplay
                :tags="row.account.tags"
                small
              />
            </template>
            <template v-else>
              <HashLink
                :text="row.address"
                location="ethereum"
              />
              <div class="text-xs text-rui-text-secondary">
                {{ t('queried_address_dialog.untracked') }}
              </div>
            </template>
          </div>
          <RuiTooltip
            :options="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                variant="text"
                icon
                size="sm"
                color="error"
                data-testid="queried-address-remove"
                @click="
                  deleteQueriedAddress({
                    module,
                    address: row.address,
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
        class="mt-2 rounded-rui-control border border-dashed border-rui-divider px-3 py-3 text-sm text-rui-text-secondary"
        data-testid="queried-address-empty"
      >
        {{
          t('queried_address_dialog.all_address_queried', {
            module: currentModule?.name,
          })
        }}
      </div>
    </RuiCard>
  </RuiDialog>
</template>
