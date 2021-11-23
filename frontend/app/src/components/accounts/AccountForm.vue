<template>
  <v-form
    ref="form"
    :value="value"
    data-cy="blockchain-balance-form"
    @input="input"
  >
    <v-row no-gutters>
      <v-col cols="12">
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
      </v-col>
    </v-row>
    <v-row v-if="!edit" no-gutters class="mb-5">
      <v-col cols="12">
        <input-mode-select v-model="inputMode" :blockchain="blockchain" />
      </v-col>
    </v-row>
    <v-row v-if="displayXpubInput" align="center" no-gutters class="mt-2">
      <v-col cols="auto">
        <v-select
          v-model="xpubKeyPrefix"
          outlined
          class="account-form__xpub-key-type"
          item-value="value"
          item-text="label"
          :disabled="accountOperation || loading || !!edit"
          :items="keyType"
        />
      </v-col>
      <v-col>
        <v-text-field
          v-model="xpub"
          outlined
          class="account-form__xpub ml-2"
          :label="$t('account_form.labels.btc.xpub')"
          autocomplete="off"
          :error-messages="errorMessages[fields.XPUB]"
          :disabled="accountOperation || loading || !!edit"
          @paste="onPasteXpub"
        >
          <template #append-outer>
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <div class="account-form__advanced">
                  <v-btn
                    icon
                    v-bind="attrs"
                    v-on="on"
                    @click="advanced = !advanced"
                  >
                    <v-icon v-if="advanced">mdi-chevron-up</v-icon>
                    <v-icon v-else>mdi-chevron-down</v-icon>
                  </v-btn>
                </div>
              </template>
              <span>
                {{ $tc('account_form.advanced_tooltip', advanced ? 0 : 1) }}
              </span>
            </v-tooltip>
          </template>
        </v-text-field>
      </v-col>
    </v-row>
    <v-row v-if="isBtc && isXpub && advanced" no-gutters>
      <v-col>
        <v-text-field
          v-model="derivationPath"
          outlined
          class="account-form__derivation-path"
          :label="$t('account_form.labels.btc.derivation_path')"
          :error-messages="errorMessages[fields.DERIVATION_PATH]"
          autocomplete="off"
          :disabled="accountOperation || loading || !!edit"
          persistent-hint
          :hint="$t('account_form.labels.btc.derivation_path_hint')"
        />
      </v-col>
    </v-row>
    <v-row v-if="isEth" no-gutters>
      <v-col>
        <module-activator @update:selection="selectedModules = $event" />
      </v-col>
    </v-row>
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
    <v-row no-gutters>
      <v-col cols="12">
        <v-text-field
          v-model="label"
          data-cy="account-label-field"
          outlined
          class="account-form__label"
          :label="$t('account_form.labels.label')"
          :disabled="accountOperation || loading"
        />
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col cols="12">
        <tag-input
          v-model="tags"
          data-cy="account-tag-field"
          outlined
          :disabled="accountOperation || loading"
        />
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col cols="12">
        <div class="account-form--progress">
          <v-progress-linear v-if="accountOperation" indeterminate />
        </div>
      </v-col>
    </v-row>
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
  watch
} from '@vue/composition-api';
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
type XpubType = {
  readonly label: string;
  readonly value: string;
};

const XPUB_LABEL = 'P2PKH';
const XPUB_VALUE = 'xpub';
const YPUB_LABEL = 'P2SH-P2WPKH';
const YPUB_VALUE = 'ypub';
const ZPUB_LABEL = 'WPKH';
const ZPUB_VALUE = 'zpub';
const XPUB_TYPE = 'p2pkh';
const YPUB_TYPE = 'p2sh_p2wpkh';
const ZPUB_TYPE = 'wpkh';

const XPUB_KEY_PREFIX = [XPUB_VALUE, YPUB_VALUE, ZPUB_VALUE] as const;
const XPUB_KEY_TYPE = [XPUB_TYPE, YPUB_TYPE, ZPUB_TYPE] as const;

type XpubPrefix = typeof XPUB_KEY_PREFIX[number];
type XpubKeyType = typeof XPUB_KEY_TYPE[number];

const getKeyType: (key: XpubPrefix) => XpubKeyType = key => {
  if (key === XPUB_VALUE) {
    return XPUB_TYPE;
  } else if (key === YPUB_VALUE) {
    return YPUB_TYPE;
  } else if (key === ZPUB_VALUE) {
    return ZPUB_TYPE;
  }
  throw new Error(`${key} is not acceptable`);
};

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
  components: { ModuleActivator, InputModeSelect, TagInput },
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
    const xpub = ref('');
    const derivationPath = ref('');
    const xpubKeyPrefix = ref<XpubPrefix>(XPUB_VALUE);

    const address = ref('');
    const addresses = ref('');

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
    const advanced = ref(false);

    const selectedModules = ref<Module[]>([]);

    watch(address, () => {
      clearErrors(FIELD_ADDRESS);
    });
    watch(xpub, value => {
      if (!value) {
        return;
      }
      clearErrors(FIELD_XPUB);
      setXpubKeyType(value);
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
    watch(derivationPath, () => {
      clearErrors(FIELD_DERIVATION_PATH);
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

    const isPrefixed = (value: string) => value.match(/([xzy]pub)(.*)/);
    const setXpubKeyType = (value: string) => {
      const match = isPrefixed(value);
      if (match && match.length === 3) {
        const prefix = match[1] as XpubPrefix;
        if (prefix === XPUB_VALUE) {
          return;
        }
        xpubKeyPrefix.value = prefix;
      }
    };

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
        const match = isPrefixed(account.xpub);
        if (match) {
          xpub.value = match[0];
          xpubKeyPrefix.value = match[1] as XpubPrefix;
        } else {
          xpub.value = account.xpub;
        }

        derivationPath.value = account.derivationPath;
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
      xpub.value = '';
      derivationPath.value = '';
      form.value?.resetValidation();
      blockchain.value = Blockchain.ETH;
      inputMode.value = MANUAL_ADD;
      multiple.value = false;
    };

    const payload = computed<BlockchainAccountPayload>(() => {
      let xpubPayload: XpubPayload | undefined;
      if (isBtc.value && isXpub.value) {
        const trimmedKey = xpub.value.trim();
        xpubPayload = {
          xpub: trimmedKey,
          derivationPath: derivationPath.value ?? undefined,
          xpubType: getKeyType(xpubKeyPrefix.value)
        };
      } else {
        xpubPayload = undefined;
      }

      return {
        blockchain: blockchain.value,
        address: address.value.trim(),
        label: label.value,
        tags: tags.value,
        xpub: xpubPayload,
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
      XPUB: FIELD_XPUB,
      ADDRESS: FIELD_ADDRESS,
      DERIVATION_PATH: FIELD_DERIVATION_PATH
    };

    const keyType: XpubType[] = [
      {
        label: XPUB_LABEL,
        value: XPUB_VALUE
      },
      {
        label: YPUB_LABEL,
        value: YPUB_VALUE
      },
      {
        label: ZPUB_LABEL,
        value: ZPUB_VALUE
      }
    ];

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

    const onPasteXpub = (event: ClipboardEvent) => {
      const paste = trimOnPaste(event);
      if (paste) {
        setXpubKeyType(paste);
        xpub.value = paste;
      }
    };

    return {
      form,
      items: Object.values(Blockchain),
      xpub,
      xpubKeyPrefix,
      derivationPath,
      address,
      addresses,
      entries,
      label,
      tags,
      blockchain,
      inputMode,
      multiple,
      pending,
      advanced,
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
      keyType,
      onPasteMulti,
      onPasteXpub,
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
