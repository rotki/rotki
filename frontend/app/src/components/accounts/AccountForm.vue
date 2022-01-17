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
      v-if="isXpub"
      :disabled="loading || !!edit"
      :error-messages="errorMessages"
      :xpub="xpub"
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
        :label="$t('account_form.labels.label')"
        :disabled="loading"
      />

      <tag-input
        v-model="tags"
        data-cy="account-tag-field"
        outlined
        :disabled="loading"
      />
    </div>

    <div class="account-form--progress">
      <v-progress-linear v-if="accountOperation" indeterminate />
    </div>
  </v-form>
</template>
<script lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  computed,
  defineComponent,
  onMounted,
  PropType,
  ref,
  toRefs,
  unref,
  watch
} from '@vue/composition-api';
import AddressInput from '@/components/accounts/blockchain/AddressInput.vue';
import ChainSelect from '@/components/accounts/blockchain/ChainSelect.vue';
import Eth2Input from '@/components/accounts/blockchain/Eth2Input.vue';
import { xpubToPayload } from '@/components/accounts/blockchain/xpub';
import XpubInput from '@/components/accounts/blockchain/XpubInput.vue';
import {
  MANUAL_ADD,
  METAMASK_IMPORT,
  XPUB_ADD
} from '@/components/accounts/const';
import InputModeSelect from '@/components/accounts/InputModeSelect.vue';
import ModuleActivator from '@/components/accounts/ModuleActivator.vue';
import { AccountInput } from '@/components/accounts/types';
import TagInput from '@/components/inputs/TagInput.vue';
import { setupBlockchainAccounts } from '@/composables/balances';
import { setupMessages } from '@/composables/common';
import { setupTaskStatus } from '@/composables/tasks';
import { useInterop } from '@/electron-interop';
import i18n from '@/i18n';
import { deserializeApiErrorMessage } from '@/services/converters';
import {
  AccountPayload,
  BlockchainAccountPayload,
  BlockchainAccountWithBalance,
  XpubPayload
} from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { Severity } from '@/store/notifications/consts';
import { Eth2Validator } from '@/types/balances';
import { Module } from '@/types/modules';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { getMetamaskAddresses } from '@/utils/metamask';

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

const AccountForm = defineComponent({
  name: 'AccountForm',
  components: {
    Eth2Input,
    ChainSelect,
    AddressInput,
    XpubInput,
    ModuleActivator,
    InputModeSelect,
    TagInput
  },
  props: {
    value: { required: true, type: Boolean, default: false },
    edit: {
      required: false,
      default: null,
      type: Object as PropType<BlockchainAccountWithBalance | null>
    },
    context: { required: true, type: String as PropType<Blockchain> }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { context, edit } = toRefs(props);

    const isEdit = computed(() => !!edit.value);
    const xpub = ref<XpubPayload | null>(null);
    const addresses = ref<string[]>([]);
    const validator = ref<Eth2Validator | null>(null);
    const label = ref('');
    const tags = ref<string[]>([]);
    const blockchain = ref<Blockchain>(Blockchain.ETH);
    const inputMode = ref<AccountInput>(MANUAL_ADD);
    const form = ref<any>(null);
    const errorMessages = ref(validationErrors());
    const pending = ref(false);
    const selectedModules = ref<Module[]>([]);

    const setErrors = (field: keyof ValidationErrors, messages: string[]) => {
      const errors = { ...errorMessages.value };
      errors[field].push(...messages);
      errorMessages.value = errors;
      input(false);
    };

    const clearErrors = (field: keyof ValidationErrors) => {
      const messages = errorMessages.value[field];
      if (messages.length === 0) {
        return;
      }

      for (let i = 0; i < messages.length; i++) {
        messages.pop();
      }
      input(true);
    };
    watch(blockchain, () => {
      form.value?.resetValidation();
      clearErrors('address');
    });
    watch(xpub, () => {
      clearErrors(FIELD_XPUB);
      clearErrors(FIELD_DERIVATION_PATH);
    });
    watch(addresses, () => clearErrors(FIELD_ADDRESS));
    watch(edit, () => setEditMode());
    watch(blockchain, value => {
      if (unref(edit)) {
        return;
      }
      if (value === Blockchain.BTC) {
        inputMode.value = XPUB_ADD;
      } else {
        inputMode.value = MANUAL_ADD;
      }
    });
    watch(context, () => {
      if (!edit.value) {
        return;
      }
      blockchain.value = context.value;
    });

    const isEth = computed(() => blockchain.value === Blockchain.ETH);
    const isEth2 = computed(() => blockchain.value === Blockchain.ETH2);
    const isBtc = computed(() => blockchain.value === Blockchain.BTC);
    const isXpub = computed(() => inputMode.value === XPUB_ADD);
    const isMetamask = computed(() => inputMode.value === METAMASK_IMPORT);

    const setEditMode = () => {
      const account = unref(edit);
      if (!account) {
        return;
      }

      if (account.chain === Blockchain.ETH2) {
        assert('ownershipPercentage' in account);
        validator.value = {
          publicKey: account.address,
          ownershipPercentage: account.ownershipPercentage,
          validatorIndex: account.label
        };
      }

      addresses.value = [account.address];
      blockchain.value = account.chain;
      label.value = account.label;
      tags.value = account.tags;
      if ('xpub' in account) {
        xpub.value = xpubToPayload(account.xpub, account.derivationPath);
        inputMode.value = account.address ? MANUAL_ADD : XPUB_ADD;
      }
    };

    onMounted(() => {
      setEditMode();
      if (!isEdit.value) {
        blockchain.value = context.value;
      }
    });

    const reset = () => {
      addresses.value = [];
      label.value = '';
      tags.value = [];
      form.value?.resetValidation();
      blockchain.value = Blockchain.ETH;
      inputMode.value = MANUAL_ADD;
    };

    const payload = computed<BlockchainAccountPayload>(() => {
      return {
        blockchain: unref(blockchain),
        address: unref(addresses)[0],
        label: label.value,
        tags: tags.value,
        xpub: unref(xpub) ?? undefined,
        modules: isEth.value ? selectedModules.value : undefined
      };
    });

    const input = (isValid: boolean) => {
      emit('input', isValid);
    };

    const { isTaskRunning } = setupTaskStatus();

    const accountOperation = computed(
      () =>
        isTaskRunning(TaskType.ADD_ACCOUNT).value ||
        isTaskRunning(TaskType.REMOVE_ACCOUNT).value ||
        pending.value
    );

    const loading = computed(
      () =>
        accountOperation.value ||
        isTaskRunning(TaskType.QUERY_BALANCES).value ||
        isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES).value
    );

    const {
      addAccount,
      addAccounts,
      editAccount,
      addEth2Validator,
      editEth2Validator
    } = setupBlockchainAccounts();

    const metamaskImport = async () => {
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
          label: label.value,
          tags: tags.value
        }));

        await addAccounts({
          blockchain: Blockchain.ETH,
          payload: payload,
          modules: selectedModules.value
        });
        return true;
      } catch (e: any) {
        const title = i18n
          .t('blockchain_balances.metamask_import.error.title')
          .toString();
        const description = i18n
          .t('blockchain_balances.metamask_import.error.description', {
            error: e.message
          })
          .toString();
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

    const { setMessage } = setupMessages();

    const manualAdd = async () => {
      const blockchainAccount = unref(payload);
      try {
        if (unref(isEdit)) {
          await editAccount(blockchainAccount);
        } else {
          const entries = unref(addresses);
          if (entries.length > 1) {
            const payload = entries.map(address => ({
              address: address,
              label: unref(label),
              tags: unref(tags)
            }));
            await addAccounts({
              blockchain: unref(blockchain),
              payload,
              modules: unref(isEth) ? unref(selectedModules) : undefined
            });
          } else {
            await addAccount(blockchainAccount);
          }
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
          pending.value = false;
          return false;
        }
        await setMessage({
          description: i18n
            .t('account_form.error.description', {
              error: e.message
            })
            .toString(),
          title: i18n.t('account_form.error.title').toString(),
          success: false
        });
        return false;
      }
      return true;
    };

    const save = async () => {
      let result: boolean;
      pending.value = true;

      if (unref(isMetamask)) {
        result = await metamaskImport();
      } else if (unref(isEth2)) {
        const payload = unref(validator);
        assert(payload);
        result = await (edit.value
          ? editEth2Validator(payload)
          : addEth2Validator(payload));
      } else {
        result = await manualAdd();
      }

      pending.value = false;
      return result;
    };

    return {
      form,
      addresses,
      xpub,
      validator,
      label,
      tags,
      blockchain,
      inputMode,
      pending,
      selectedModules,
      errorMessages,
      isEth,
      isEth2,
      isBtc,
      isXpub,
      isMetamask,
      loading,
      accountOperation,
      input,
      save,
      reset
    };
  }
});

export default AccountForm;
export type AccountFormType = InstanceType<typeof AccountForm>;
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
