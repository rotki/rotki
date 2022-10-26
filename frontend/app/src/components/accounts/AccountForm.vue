<template>
  <v-form
    ref="form"
    :value="value"
    data-cy="blockchain-balance-form"
    @input="input"
  >
    <chain-select
      :disabled="loading || !!edit"
      :blockchain="blockchain"
      @update:blockchain="blockchain = $event"
    />

    <input-mode-select
      v-if="!edit"
      v-model="inputMode"
      :blockchain="blockchain"
    />

    <xpub-input
      v-if="
        isXpub &&
        (blockchain === Blockchain.BTC || blockchain === Blockchain.BCH)
      "
      :disabled="loading || !!edit"
      :error-messages="errorMessages"
      :xpub="xpub"
      :blockchain="blockchain"
      @update:xpub="xpub = $event"
    />

    <module-activator
      v-if="isEth"
      @update:selection="selectedModules = $event"
    />

    <address-input
      v-if="!(isXpub || isMetamask || isEth2)"
      :addresses="addresses"
      :error-messages="errorMessages"
      :disabled="loading || !!edit"
      :multi="!edit && !isXpub"
      @update:addresses="addresses = $event"
    />

    <eth2-input
      v-if="isEth2"
      :validator="validator"
      :disabled="loading || !!edit"
      @update:validator="validator = $event"
    />
    <div v-else>
      <v-text-field
        v-model="label"
        data-cy="account-label-field"
        outlined
        class="account-form__label"
        :label="t('common.name')"
        :disabled="loading"
      />

      <tag-input
        v-model="tags"
        data-cy="account-tag-field"
        outlined
        :disabled="loading"
      />
    </div>
  </v-form>
</template>
<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Severity } from '@rotki/common/lib/messages';
import { PropType } from 'vue';
import AddressInput from '@/components/accounts/blockchain/AddressInput.vue';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import XpubInput from '@/components/accounts/blockchain/XpubInput.vue';
import InputModeSelect from '@/components/accounts/InputModeSelect.vue';
import ModuleActivator from '@/components/accounts/ModuleActivator.vue';
import TagInput from '@/components/inputs/TagInput.vue';
import { setupTaskStatus } from '@/composables/tasks';
import { useInterop } from '@/electron-interop';
import { deserializeApiErrorMessage } from '@/services/converters';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import {
  AccountPayload,
  BlockchainAccountPayload,
  BlockchainAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { useBlockchainStore } from '@/store/blockchain';
import { useBlockchainAccountsStore } from '@/store/blockchain/accounts';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';
import { useMessageStore } from '@/store/message';
import { useNotifications } from '@/store/notifications';
import {
  AccountInput,
  MANUAL_ADD,
  METAMASK_IMPORT,
  XPUB_ADD
} from '@/types/account-input';
import { Eth2Validator } from '@/types/balances';
import { Module } from '@/types/modules';
import { TaskType } from '@/types/task-type';
import { startPromise } from '@/utils';
import { assert } from '@/utils/assertions';
import { getMetamaskAddresses } from '@/utils/metamask';
import { xpubToPayload } from '@/utils/xpub';

const FIELD_ADDRESS = 'address';
const FIELD_XPUB = 'xpub';
const FIELD_DERIVATION_PATH = 'derivation_path';

const FIELDS = [FIELD_ADDRESS, FIELD_XPUB, FIELD_DERIVATION_PATH] as const;
type ValidationFields = typeof FIELDS[number];
type ValidationErrors = { [field in ValidationFields]: string[] };

const validationErrors: () => ValidationErrors = () => ({
  [FIELD_XPUB]: [],
  [FIELD_ADDRESS]: [],
  [FIELD_DERIVATION_PATH]: []
});

const props = defineProps({
  value: { required: true, type: Boolean, default: false },
  edit: {
    required: false,
    default: null,
    type: Object as PropType<BlockchainAccountWithBalance | null>
  },
  context: { required: true, type: String as PropType<Blockchain> },
  pending: { required: false, type: Boolean, default: false }
});

const emit = defineEmits<{
  (e: 'input', valid: boolean): void;
  (e: 'update:pending', pending: boolean): void;
}>();

const { context, edit, pending } = toRefs(props);
const { t } = useI18n();

const isEdit = computed(() => !!get(edit));
const xpub = ref<XpubPayload | null>(null);
const addresses = ref<string[]>([]);
const validator = ref<Eth2Validator | null>(null);
const label = ref('');
const tags = ref<string[]>([]);
const blockchain = ref<Blockchain>(Blockchain.ETH);
const inputMode = ref<AccountInput>(MANUAL_ADD);
const form = ref<any>(null);
const errorMessages = ref(validationErrors());
const selectedModules = ref<Module[]>([]);
const valid = ref<boolean>(true);

const updatePending = (pending: boolean) => emit('update:pending', pending);

const setErrors = (field: keyof ValidationErrors, messages: string[]) => {
  const errors = { ...get(errorMessages) };
  errors[field].push(...messages);
  set(errorMessages, errors);
  set(valid, false);
  input(false);
};

const clearErrors = (field: keyof ValidationErrors) => {
  const messages = get(errorMessages)[field];
  if (messages.length === 0) {
    return;
  }

  for (let i = 0; i < messages.length; i++) {
    messages.pop();
  }
  set(valid, true);
  input(true);
};
watch(blockchain, () => {
  get(form)?.resetValidation();
  clearErrors('address');
});
watch(xpub, () => {
  clearErrors(FIELD_XPUB);
  clearErrors(FIELD_DERIVATION_PATH);
});
watch(addresses, () => clearErrors(FIELD_ADDRESS));
watch(edit, () => setEditMode());
watch(blockchain, value => {
  if (get(edit)) {
    return;
  }
  if ([Blockchain.BTC, Blockchain.BCH].includes(value)) {
    set(inputMode, XPUB_ADD);
  } else {
    set(inputMode, MANUAL_ADD);
  }
});
watch(context, () => {
  if (!get(edit)) {
    return;
  }
  set(blockchain, get(context));
});

const isEth = computed(() => get(blockchain) === Blockchain.ETH);
const isEth2 = computed(() => get(blockchain) === Blockchain.ETH2);
const isXpub = computed(() => get(inputMode) === XPUB_ADD);
const isMetamask = computed(() => get(inputMode) === METAMASK_IMPORT);

const setEditMode = () => {
  const account = get(edit);
  if (!account) {
    return;
  }

  if (account.chain === Blockchain.ETH2) {
    assert('ownershipPercentage' in account);
    set(validator, {
      publicKey: account.address,
      ownershipPercentage: account.ownershipPercentage,
      validatorIndex: account.label
    });
  }

  set(addresses, [account.address]);
  set(blockchain, account.chain);
  set(label, account.label);
  set(tags, account.tags);
  if ('xpub' in account) {
    set(xpub, xpubToPayload(account.xpub, account.derivationPath));
    set(inputMode, account.address ? MANUAL_ADD : XPUB_ADD);
  }
};

onMounted(() => {
  setEditMode();
  if (!get(isEdit)) {
    set(blockchain, get(context));
  }
});

const reset = () => {
  set(addresses, []);
  set(label, '');
  set(tags, []);
  get(form)?.resetValidation();
  set(blockchain, Blockchain.ETH);
  set(inputMode, MANUAL_ADD);
};

const payload = computed<BlockchainAccountPayload>(() => {
  return {
    blockchain: get(blockchain),
    address: get(addresses)[0],
    label: get(label),
    tags: get(tags),
    xpub: get(inputMode) === XPUB_ADD ? get(xpub) ?? undefined : undefined,
    modules: get(isEth) ? get(selectedModules) : undefined
  };
});

const input = (isValid: boolean) => {
  emit('input', isValid);
};

const { isTaskRunning } = setupTaskStatus();

const accountOperation = computed<boolean>(
  () =>
    get(isTaskRunning(TaskType.ADD_ACCOUNT)) ||
    get(isTaskRunning(TaskType.REMOVE_ACCOUNT)) ||
    get(pending)
);

const loading = computed<boolean>(
  () =>
    get(accountOperation) ||
    get(isTaskRunning(TaskType.QUERY_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES))
);

watch(loading, loading => {
  input(get(valid) && !loading);
});

const { addEth2Validator, editEth2Validator } = useEthAccountsStore();
const { addAccounts, refreshAccounts } = useBlockchainStore();
const { editAccount } = useBlockchainAccountsStore();
const { fetchEnsNames } = useEthNamesStore();

const metamaskImport = async (): Promise<boolean> => {
  const interop = useInterop();
  try {
    let addresses: string[];
    if (interop.isPackaged) {
      addresses = await interop.metamaskImport();
    } else {
      addresses = await getMetamaskAddresses();
    }

    const payload: AccountPayload[] = addresses.map(value => ({
      address: value,
      label: get(label),
      tags: get(tags)
    }));

    await addAccounts({
      blockchain: Blockchain.ETH,
      payload: payload,
      modules: get(selectedModules)
    });
    return true;
  } catch (e: any) {
    const title = t(
      'blockchain_balances.metamask_import.error.title'
    ).toString();
    const description = t(
      'blockchain_balances.metamask_import.error.description',
      {
        error: e.message
      }
    ).toString();
    const { notify } = useNotifications();
    notify({
      title,
      message: description,
      severity: Severity.ERROR,
      display: true
    });
    return false;
  }
};

const { setMessage } = useMessageStore();

const manualAdd = async () => {
  const blockchainAccount = get(payload);
  try {
    if (get(isEdit)) {
      await editAccount(blockchainAccount);

      if (get(blockchain) === Blockchain.ETH) {
        await fetchEnsNames([blockchainAccount.address], true);
      }
      startPromise(refreshAccounts(blockchainAccount.blockchain));
    } else {
      const entries = get(addresses);
      const payload = entries.map(address => ({
        address: address,
        label: get(label),
        tags: get(tags)
      }));
      await addAccounts({
        blockchain: get(blockchain),
        payload: entries.length > 1 ? payload : [blockchainAccount],
        modules: get(isEth) ? get(selectedModules) : undefined
      });
    }

    reset();
  } catch (e: any) {
    const apiErrorMessage = deserializeApiErrorMessage(e.message);
    if (apiErrorMessage && Object.keys(apiErrorMessage).length > 0) {
      const errors: ValidationErrors = validationErrors();
      clearErrors(FIELD_ADDRESS);
      clearErrors(FIELD_XPUB);
      clearErrors(FIELD_DERIVATION_PATH);

      for (const field of FIELDS) {
        if (!(field in apiErrorMessage)) {
          continue;
        }

        errors[field] = errors[field].concat(apiErrorMessage[field]);
      }

      setErrors(FIELD_ADDRESS, errors[FIELD_ADDRESS]);
      setErrors(FIELD_XPUB, errors[FIELD_XPUB]);
      setErrors(FIELD_DERIVATION_PATH, errors[FIELD_DERIVATION_PATH]);
      updatePending(false);
      return false;
    }
    await setMessage({
      description: t('account_form.error.description', {
        error: e.message
      }).toString(),
      title: t('account_form.error.title').toString(),
      success: false
    });
    return false;
  }
  return true;
};

const save = async () => {
  let result: boolean;
  updatePending(true);

  if (get(isMetamask)) {
    result = await metamaskImport();
  } else if (get(isEth2)) {
    const payload = get(validator);
    assert(payload);
    result = await (get(edit)
      ? editEth2Validator(payload)
      : addEth2Validator(payload));
    startPromise(refreshAccounts(Blockchain.ETH2));
  } else {
    result = await manualAdd();
  }

  updatePending(false);
  return result;
};

defineExpose({
  save,
  reset
});
</script>
<style scoped lang="scss">
.account-form {
  &__xpub-key-type {
    max-width: 150px;
  }

  &__buttons {
    &__cancel {
      margin-left: 8px;
    }
  }

  &--progress {
    height: 15px;
  }

  &__advanced {
    max-height: 56px;
    margin-top: -6px;
  }
}
</style>
