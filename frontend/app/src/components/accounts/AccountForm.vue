<template>
  <v-form
    ref="form"
    :value="value"
    data-cy="blockchain-balance-form"
    @input="input"
  >
    <v-select
      v-model="blockchain"
      data-cy="account-blockchain-field"
      outlined
      class="account-form__chain pt-2"
      :items="items"
      :label="$t('account_form.labels.blockchain')"
      :disabled="accountOperation || loading || !!edit"
    >
      <template #selection="{ item }">
        <asset-details class="pt-2 pb-2" :asset="item" />
      </template>
      <template #item="{ item }">
        <asset-details class="pt-2 pb-2" :asset="item" />
      </template>
    </v-select>

    <input-mode-select
      v-if="!edit"
      v-model="inputMode"
      :blockchain="blockchain"
    />

    <xpub-input
      v-if="displayXpubInput"
      :disabled="accountOperation || loading || !!edit"
      :error-messages="errorMessages"
      :xpub="xpub"
      @update:xpub="xpub = $event"
    />

    <module-activator
      v-if="isEth"
      @update:selection="selectedModules = $event"
    />

    <v-row
      v-if="
        (!isBtc || (isBtc && !isXpub) || !!edit) &&
        !isMetamask &&
        !(isXpub && !!edit)
      "
      no-gutters
      class="mt-2"
    >
      <v-col>
        <v-row v-if="!edit && !isXpub" no-gutters align="center">
          <v-col cols="auto">
            <v-checkbox
              v-model="multiple"
              :disabled="accountOperation || loading || !!edit"
              :label="$t('account_form.labels.multiple')"
            />
          </v-col>
        </v-row>
        <v-text-field
          v-if="!multiple"
          v-model="address"
          data-cy="account-address-field"
          outlined
          class="account-form__address"
          :label="$t('account_form.labels.account')"
          :rules="rules"
          :error-messages="errorMessages[fields.ADDRESS]"
          autocomplete="off"
          :disabled="accountOperation || loading || !!edit"
          @paste="onPasteAddress"
        />
        <v-textarea
          v-else
          v-model="addresses"
          outlined
          :disabled="accountOperation || loading || !!edit"
          :hint="$t('account_form.labels.addresses_hint')"
          :label="$t('account_form.labels.addresses')"
          @paste="onPasteMulti"
        />
        <v-row v-if="multiple" no-gutters>
          <v-col>
            <div
              class="text-caption"
              v-text="
                $tc('account_form.labels.addresses_entries', entries.length, {
                  count: entries.length
                })
              "
            />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <v-text-field
      v-model="label"
      data-cy="account-label-field"
      outlined
      class="account-form__label"
      :label="$t('account_form.labels.label')"
      :disabled="accountOperation || loading"
    />
    <tag-input
      v-model="tags"
      data-cy="account-tag-field"
      outlined
      :disabled="accountOperation || loading"
    />
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
  Ref,
  ref,
  toRefs,
  unref,
  watch
} from '@vue/composition-api';
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
  BlockchainAccount,
  BlockchainAccountPayload,
  XpubPayload
} from '@/store/balances/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { Module } from '@/types/modules';
import { TaskType } from '@/types/task-type';
import { trimOnPaste } from '@/utils/event';
import { getMetamaskAddresses } from '@/utils/metamask';

type ValidationRule = (value: string) => boolean | string;

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

const setupValidationRules = (
  isEdit: Ref<boolean>,
  isMetamask: Ref<boolean>
) => {
  const nonEmptyRule = (value: string) => {
    return (
      !!value || i18n.t('account_form.validation.address_non_empty').toString()
    );
  };

  const rules = computed<ValidationRule[]>(() => {
    if (isMetamask.value) {
      return [];
    }
    return [nonEmptyRule];
  });

  return { rules };
};

const AccountForm = defineComponent({
  name: 'AccountForm',
  components: { XpubInput, ModuleActivator, InputModeSelect, TagInput },
  props: {
    value: { required: true, type: Boolean, default: false },
    edit: {
      required: false,
      default: null,
      type: Object as PropType<BlockchainAccount | null>
    },
    context: { required: true, type: String as PropType<Blockchain> }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { context, edit } = toRefs(props);

    const isEdit = computed(() => !!edit.value);

    const address = ref('');
    const addresses = ref('');
    const xpub = ref<XpubPayload | null>(null);

    const entries = computed(() => {
      const allAddresses = addresses.value
        .split(',')
        .map(value => value.trim())
        .filter(entry => entry.length > 0);

      const entries: { [address: string]: string } = {};
      for (const address of allAddresses) {
        const lowerCase = address.toLocaleLowerCase();
        if (entries[lowerCase]) {
          continue;
        }
        entries[lowerCase] = address;
      }
      return Object.values(entries);
    });

    const label = ref('');
    const tags = ref<string[]>([]);
    const blockchain = ref<Blockchain>(Blockchain.ETH);
    const inputMode = ref<AccountInput>(MANUAL_ADD);

    const form = ref<any>(null);

    const errorMessages = ref(validationErrors());

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

    const pending = ref(false);
    const multiple = ref(false);

    const selectedModules = ref<Module[]>([]);
    watch(xpub, () => {
      clearErrors(FIELD_XPUB);
      clearErrors(FIELD_DERIVATION_PATH);
    });

    watch(address, () => {
      clearErrors(FIELD_ADDRESS);
    });
    watch(multiple, () => {
      addresses.value = '';
      address.value = '';
    });
    watch(edit, () => {
      setEditMode();
    });
    watch(blockchain, value => {
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
    const isBtc = computed(() => blockchain.value === Blockchain.BTC);

    const isXpub = computed(() => {
      return inputMode.value === XPUB_ADD;
    });

    const isMetamask = computed(() => {
      return inputMode.value === METAMASK_IMPORT;
    });

    const displayXpubInput = computed(() => {
      const isEdit = !!edit.value;
      return (
        (!isEdit && isBtc.value && isXpub.value) || (isEdit && !!xpub.value)
      );
    });

    const setEditMode = () => {
      const account = edit.value;
      if (!account) {
        return;
      }

      address.value = account.address;
      blockchain.value = account.chain;
      label.value = account.label;
      tags.value = account.tags;
      if ('xpub' in account) {
        xpub.value = xpubToPayload(account.xpub, account.derivationPath);
      }
    };

    onMounted(() => {
      setEditMode();
      if (!isEdit.value) {
        blockchain.value = context.value;
      }
    });

    const reset = () => {
      address.value = '';
      addresses.value = '';
      label.value = '';
      tags.value = [];
      form.value?.resetValidation();
      blockchain.value = Blockchain.ETH;
      inputMode.value = MANUAL_ADD;
      multiple.value = false;
    };

    const payload = computed<BlockchainAccountPayload>(() => {
      return {
        blockchain: blockchain.value,
        address: address.value.trim(),
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
        isTaskRunning(TaskType.QUERY_BALANCES).value ||
        isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES).value
    );

    const { addAccount, addAccounts, editAccount } = setupBlockchainAccounts();

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
        notify(description, title, Severity.ERROR, true);
        return false;
      }
    };

    const { setMessage } = setupMessages();

    const manualAdd = async () => {
      const blockchainAccount = payload.value;
      try {
        if (isEdit.value) {
          await editAccount(blockchainAccount);
        } else {
          if (entries.value.length > 0) {
            const payload = entries.value.map(address => ({
              address: address,
              label: label.value,
              tags: tags.value
            }));
            await addAccounts({
              blockchain: blockchain.value,
              payload,
              modules: isEth.value ? selectedModules.value : undefined
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

      if (isMetamask.value) {
        result = await metamaskImport();
      } else {
        result = await manualAdd();
      }

      pending.value = false;
      return result;
    };

    const fields = {
      ADDRESS: FIELD_ADDRESS
    };

    const onPasteMulti = (event: ClipboardEvent) => {
      const paste = trimOnPaste(event);
      if (paste) {
        addresses.value += paste.replace(/,(0x)/g, ',\n0x');
      }
    };

    const onPasteAddress = (event: ClipboardEvent) => {
      const paste = trimOnPaste(event);
      if (paste) {
        address.value = paste;
      }
    };

    return {
      form,
      items: Object.values(Blockchain),
      address,
      addresses,
      xpub,
      entries,
      label,
      tags,
      blockchain,
      inputMode,
      multiple,
      pending,
      selectedModules,
      errorMessages,
      isEth,
      isBtc,
      isXpub,
      isMetamask,
      displayXpubInput,
      loading,
      accountOperation,
      ...setupValidationRules(isEdit, isMetamask),
      fields,
      onPasteMulti,
      onPasteAddress,
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
