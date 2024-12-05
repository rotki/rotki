<script setup lang="ts">
import { groupBy } from 'lodash-es';
import { Blockchain } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { useBlockchainStore } from '@/store/blockchain';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { downloadFileByTextContent } from '@/utils/download';
import FileUpload from '@/components/import/FileUpload.vue';
import { useBlockchains } from '@/composables/blockchain';
import { isBtcChain } from '@/types/blockchain/chains';
import {
  type AccountPayload,
  type AddAccountsPayload,
  type XpubAccountPayload,
  XpubKeyType,
} from '@/types/blockchain/accounts';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSupportedChains } from '@/composables/info/chains';
import { useTagStore } from '@/store/session/tags';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import {
  type StakingValidatorManage,
  useAccountManage,
} from '@/composables/accounts/blockchain/use-account-manage';
import { useNotificationsStore } from '@/store/notifications';
import ExternalLink from '@/components/helper/ExternalLink.vue';

const { t } = useI18n();
const { accounts } = storeToRefs(useBlockchainStore());
const { evmchainsToSkipDetection } = storeToRefs(useGeneralSettingsStore());
const { isEvm, isEvmLikeChains } = useSupportedChains();
const { addAccounts, addEvmAccounts } = useBlockchains();
const { attemptTagCreation } = useTagStore();
const { isLoading } = useStatusStore();
const { save } = useAccountManage();
const { notify } = useNotificationsStore();

const blockchainLoading = isLoading(Section.BLOCKCHAIN);
const blockchainLoadingDebounced = refDebounced(blockchainLoading, 2000);
const doneLoading = logicAnd(logicNot(blockchainLoading), logicNot(blockchainLoadingDebounced));

const importFileUploader = ref<InstanceType<typeof FileUpload>>();
const importFile = ref<File>();
const importDialogOpen = ref<boolean>(false);
const loading = ref<boolean>(false);

interface GeneratedResult {
  chain: string;
  address: string;
  label?: string;
  tags?: string[];
  ownershipPercentage?: string;
  derivationPath?: string;
}

function exportBlockchainAccounts() {
  const shouldGroupEvmAccounts = get(evmchainsToSkipDetection).length === 0;
  const groupedAccounts: Record<string, GeneratedResult> = {};

  Object.entries(get(accounts)).forEach(([chain, accounts]) => {
    accounts.forEach((account) => {
      const isEvmAccount = (get(isEvm(chain)) || get(isEvmLikeChains(chain))) && shouldGroupEvmAccounts;
      const isEth2ValidatorAccount = chain === Blockchain.ETH2 && account.data.type === 'validator';

      let key: string;
      let accountData: GeneratedResult;

      // If it's children of xpub, skip it
      if (account.groupId && account.data.type !== 'xpub')
        return;

      if (isEvmAccount) {
        const address = getAccountAddress(account);
        key = `${address}#evm`;
        accountData = {
          address,
          chain: 'evm',
          label: account.label,
          tags: account.tags,
        };
      }
      else if (isEth2ValidatorAccount) {
        key = `${account.data.publicKey}#${account.chain}`;
        accountData = {
          address: account.data.publicKey,
          chain: Blockchain.ETH2,
          ownershipPercentage: account.data.ownershipPercentage,
        };
      }
      else {
        const address = getAccountAddress(account);
        key = `${address}#${account.chain}`;
        const isXpub = account.data.type === 'xpub';
        accountData = {
          address,
          chain: account.chain,
          label: account.label,
          tags: account.tags,
        };

        if (isXpub && account.data.derivationPath) {
          accountData.derivationPath = account.data.derivationPath;
        }
      }

      if (groupedAccounts[key]) {
        return;
      }

      groupedAccounts[key] = accountData;
    });
  });

  // Turn these json into csv
  const entries = Object.values(groupedAccounts);
  const fields = ['chain', 'address'];

  if (entries.some(acc => acc.label))
    fields.push('label');
  if (entries.some(acc => acc.tags?.length))
    fields.push('tags');
  if (entries.some(acc => acc.ownershipPercentage))
    fields.push('ownership percentage');
  if (entries.some(acc => acc.derivationPath))
    fields.push('derivation path');

  const csvContent = `${fields.join(',')}\n${entries
    .map(acc => fields.map((field) => {
      switch (field) {
        case 'chain': return acc.chain;
        case 'address': return acc.address;
        case 'label': return acc.label || '';
        case 'tags': return acc.tags?.join(';') || '';
        case 'ownership percentage': return acc.ownershipPercentage || '';
        case 'derivation path': return acc.derivationPath || '';
        default: return '';
      }
    }).join(','))
    .join('\n')}`;

  downloadFileByTextContent(
    csvContent,
    'blockchain-accounts.csv',
    'text/csv',
  );
}

function handleImportClick() {
  set(importDialogOpen, true);
}

async function handleAccountRestore(restoredAccounts: GeneratedResult[]) {
  const grouped = groupBy(restoredAccounts, 'chain');
  const tags = restoredAccounts.reduce<string[]>((acc, account) => {
    if (account.tags) {
      account.tags.forEach((tag) => {
        if (!acc.includes(tag)) {
          acc.push(tag);
        }
      });
    }
    return acc;
  }, []);

  const processPayload = (acc: GeneratedResult): AccountPayload => ({
    address: acc.address,
    label: acc.label,
    tags: acc.tags || null,
  });

  const tasks: [string, AddAccountsPayload | XpubAccountPayload][] = [];
  let eth2Accounts: GeneratedResult[] = [];

  for (const [chain, chainAccounts] of Object.entries(grouped)) {
    if (chain === 'evm') {
      tasks.push([
        'evm',
        { payload: chainAccounts.map(processPayload) },
      ]);
    }
    else if (isBtcChain(chain)) {
      const [xpubs, regular] = chainAccounts.reduce<[XpubAccountPayload[], AccountPayload[]]>(
        ([xpubs, regular], acc) => {
          if (acc.address.startsWith('xpub')) {
            xpubs.push({
              label: acc.label,
              tags: acc.tags || null,
              xpub: {
                derivationPath: acc.derivationPath || '',
                xpub: acc.address,
                xpubType: XpubKeyType.P2TR,
              },
            });
          }
          else {
            regular.push(processPayload(acc));
          }
          return [xpubs, regular];
        },
        [[], []],
      );

      if (regular.length > 0) {
        tasks.push([chain, { payload: regular }]);
      }
      xpubs.forEach(xpub => tasks.push([chain, xpub]));
    }
    else if (chain === Blockchain.ETH2) {
      eth2Accounts = chainAccounts;
    }
    else {
      tasks.push([
        chain,
        { payload: chainAccounts.map(processPayload) },
      ]);
    }
  }

  await Promise.all(tags.map(tag => attemptTagCreation(tag)));

  await awaitParallelExecution(
    tasks,
    ([_, payload]) => {
      if ('payload' in payload) {
        return payload.payload[0].address;
      }
      return payload.xpub.xpub;
    },
    async ([chain, payload]) => {
      if (chain === 'evm') {
        if ('payload' in payload) {
          return addEvmAccounts(payload, { wait: true });
        }
      }
      else {
        return addAccounts(chain, payload, { wait: true });
      }
    },
    1,
  );

  // Wait until accounts refreshed
  await until(blockchainLoading).toBe(true);
  await until(doneLoading).toBe(true);

  // Add only unregistered ETH2 accounts
  const registeredEth2Accounts = get(accounts)[Blockchain.ETH2];
  const eth2AccountsPayload: StakingValidatorManage[] = [];

  eth2Accounts.forEach((eth2Account) => {
    const found = registeredEth2Accounts.find(registeredAccount => getAccountAddress(registeredAccount) === eth2Account.address);

    if (found) {
      if (found.data.type === 'validator') {
        // If it's found, check the ownershipPercentage, and edit the old one if it's different
        const foundPercentage = found.data.ownershipPercentage || '100';
        const toBeAddedPercentage = eth2Account.ownershipPercentage || '100';

        if (foundPercentage !== toBeAddedPercentage) {
          eth2AccountsPayload.push({
            chain: Blockchain.ETH2,
            data: {
              ownershipPercentage: toBeAddedPercentage,
              publicKey: eth2Account.address,
              validatorIndex: found.data.index.toString(),
            },
            mode: 'edit',
            type: 'validator',
          });
        }
      }
    }
    else {
      eth2AccountsPayload.push({
        chain: Blockchain.ETH2,
        data: {
          ownershipPercentage: eth2Account.ownershipPercentage || '100',
          publicKey: eth2Account.address,
        },
        mode: 'add',
        type: 'validator',
      });
    }
  });

  if (eth2AccountsPayload.length > 0) {
    await awaitParallelExecution(
      eth2AccountsPayload,
      item => item.data.publicKey!,
      async (item) => {
        await save(item);
      },
      1,
    );
  }
}

async function importBlockchainData() {
  const file = get(importFile);
  if (!file) {
    return;
  }

  try {
    set(loading, true);
    const csvContent = await file.text();
    const [header, ...lines] = csvContent.split('\n');
    const headers = header.toLowerCase().split(',');
    const chainIndex = headers.indexOf('chain');
    const addressIndex = headers.indexOf('address');
    const labelIndex = headers.indexOf('label');
    const tagsIndex = headers.indexOf('tags');
    const ownershipPercentageIndex = headers.indexOf('ownership percentage');
    const derivationPathIndex = headers.indexOf('derivation path');

    if (chainIndex === -1 || addressIndex === -1) {
      throw new Error(t('blockchain_balances.import_error.invalid_format'));
    }

    const accounts = lines
      .filter(line => line.trim())
      .map((line) => {
        const values = line.split(',');
        const chain = values[chainIndex];
        const address = values[addressIndex];

        if (!chain || !address) {
          throw new Error(t('blockchain_balances.import_error.invalid_format'));
        }

        return {
          address,
          chain,
          ...(labelIndex !== -1 && values[labelIndex] && { label: values[labelIndex] }),
          ...(tagsIndex !== -1 && values[tagsIndex] && { tags: values[tagsIndex].split(';').filter(Boolean) }),
          ...(ownershipPercentageIndex !== -1 && values[ownershipPercentageIndex] && { ownershipPercentage: values[ownershipPercentageIndex] }),
          ...(derivationPathIndex !== -1 && values[derivationPathIndex] && { derivationPath: values[derivationPathIndex] }),
        };
      });

    handleAccountRestore(accounts);

    set(importDialogOpen, false);
    set(importFile, undefined);
    get(importFileUploader)?.removeFile();
  }
  catch (error) {
    const message = t('blockchain_balances.import_error.message', {
      error,
    });
    console.error(message);
    notify({
      display: true,
      message,
      title: t('blockchain_balances.import_blockchain_accounts'),
    });
  }
  finally {
    set(loading, false);
  }
}
</script>

<template>
  <RuiMenu
    :popper="{ placement: 'bottom-end' }"
    menu-class="max-w-[24rem]"
    close-on-content-click
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="!p-2"
        v-bind="attrs"
      >
        <RuiIcon name="more-2-fill" />
      </RuiButton>
    </template>
    <div class="py-2">
      <RuiButton
        variant="list"
        @click="exportBlockchainAccounts()"
      >
        <template #prepend>
          <RuiIcon name="file-upload-line" />
        </template>
        {{ t('blockchain_balances.export_blockchain_accounts') }}
      </RuiButton>
      <RuiButton
        variant="list"
        @click="handleImportClick()"
      >
        <template #prepend>
          <RuiIcon name="file-download-line" />
        </template>
        {{ t('blockchain_balances.import_blockchain_accounts') }}
      </RuiButton>
    </div>
  </RuiMenu>
  <RuiDialog
    v-model="importDialogOpen"
    max-width="600"
  >
    <RuiCard>
      <template #header>
        {{ t('blockchain_balances.import_blockchain_accounts') }}
      </template>
      <FileUpload
        ref="importFileUploader"
        v-model="importFile"
        source="csv"
        file-filter=".csv"
      />
      <div class="mt-2 text-caption text-rui-text-secondary">
        <i18n-t keypath="blockchain_balances.import_csv_example">
          <template #here>
            <ExternalLink
              color="primary"
              :url="externalLinks.usageGuideSection.importBlockchainAccounts"
            >
              {{ t('common.here') }}
            </ExternalLink>
          </template>
        </i18n-t>
      </div>
      <template #footer>
        <div class="grow" />
        <RuiButton
          variant="text"
          color="primary"
          @click="importDialogOpen = false"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="!importFile"
          :loading="loading"
          @click="importBlockchainData()"
        >
          {{ t('common.actions.import') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
