<template>
  <v-form ref="form" :value="value" @input="input">
    <v-row no-gutters>
      <v-col cols="12">
        <v-select
          v-model="blockchain"
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
          :error-messages="errorMessages[FIELD_XPUB]"
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
          :error-messages="errorMessages[FIELD_DERIVATION_PATH]"
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
        !isMetaMask &&
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
          outlined
          class="account-form__address"
          :label="$t('account_form.labels.account')"
          :rules="rules"
          :error-messages="errorMessages[FIELD_ADDRESS]"
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
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import {
  MANUAL_ADD,
  METAMASK_IMPORT,
  XPUB_ADD
} from '@/components/accounts/const';
import InputModeSelect from '@/components/accounts/InputModeSelect.vue';
import ModuleActivator from '@/components/accounts/ModuleActivator.vue';
import { AccountInput } from '@/components/accounts/types';
import TagInput from '@/components/inputs/TagInput.vue';
import { TaskType } from '@/model/task-type';
import { deserializeApiErrorMessage } from '@/services/converters';
import { SupportedModules } from '@/services/session/types';
import {
  AddAccountsPayload,
  BlockchainAccount,
  BlockchainAccountPayload,
  XpubPayload
} from '@/store/balances/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { Message } from '@/store/types';
import {
  Blockchain,
  BTC,
  ETH,
  GeneralAccount,
  SupportedBlockchains
} from '@/typing/types';
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

@Component({
  components: { ModuleActivator, InputModeSelect, TagInput },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning']),
    ...mapGetters('balances', ['account'])
  },
  methods: {
    ...mapActions('balances', ['addAccounts', 'editAccount', 'addAccount'])
  }
})
export default class AccountForm extends Vue {
  readonly items = SupportedBlockchains;
  isTaskRunning!: (type: TaskType) => boolean;
  blockchain: Blockchain = ETH;
  pending: boolean = false;
  xpub: string = '';
  derivationPath: string = '';
  address: string = '';
  addresses: string = '';
  label: string = '';
  tags: string[] = [];
  multiple: boolean = false;
  readonly errorMessages: ValidationErrors = validationErrors();
  xpubKeyPrefix: XpubPrefix = XPUB_VALUE;
  account!: (address: string) => GeneralAccount | undefined;
  addAccount!: (payload: BlockchainAccountPayload) => Promise<void>;
  addAccounts!: (payload: AddAccountsPayload) => Promise<void>;
  editAccount!: (payload: BlockchainAccountPayload) => Promise<void>;
  advanced: boolean = false;
  inputMode: AccountInput = MANUAL_ADD;
  selectedModules: SupportedModules[] = [];

  readonly FIELD_XPUB = FIELD_XPUB;
  readonly FIELD_ADDRESS = FIELD_ADDRESS;
  readonly FIELD_DERIVATION_PATH = FIELD_DERIVATION_PATH;

  get entries(): string[] {
    const addresses = this.addresses
      .split(',')
      .map(value => value.trim())
      .filter(entry => entry.length > 0);

    const entries: { [address: string]: string } = {};
    for (const address of addresses) {
      const lowerCase = address.toLocaleLowerCase();
      if (entries[lowerCase]) {
        continue;
      }
      entries[lowerCase] = address;
    }
    return Object.values(entries);
  }

  get isEth(): boolean {
    return this.blockchain === ETH;
  }

  get isBtc(): boolean {
    return this.blockchain === BTC;
  }

  get isXpub(): boolean {
    return this.inputMode === XPUB_ADD;
  }

  get isMetaMask(): boolean {
    return this.inputMode === METAMASK_IMPORT;
  }

  get displayXpubInput(): boolean {
    const edit = !!this.edit;
    return (!edit && this.isBtc && this.isXpub) || (edit && !!this.xpub);
  }

  get keyType(): XpubType[] {
    return [
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
  }

  get rules(): ValidationRule[] {
    const rules: ValidationRule[] = [];
    if (this.isMetaMask) {
      return rules;
    }
    rules.push(this.nonEmptyRule);
    if (!this.edit) {
      rules.push(this.checkIfExists);
    }
    return rules;
  }

  private nonEmptyRule(value: string): boolean | string {
    return !!value || this.$tc('account_form.validation.address_non_empty');
  }

  private checkIfExists(value: string): boolean | string {
    return (
      (!!value && !this.account(value)) ||
      this.$tc('account_form.validation.address_exists')
    );
  }

  @Prop({ required: false, default: null })
  edit!: BlockchainAccount | null;
  @Prop({ required: true, type: Boolean, default: false })
  value!: boolean;

  private setEditMode() {
    if (!this.edit) {
      return;
    }

    this.address = this.edit.address;
    this.blockchain = this.edit.chain;
    this.label = this.edit.label;
    this.tags = this.edit.tags;
    if ('xpub' in this.edit) {
      const match = this.edit.xpub.match(/([xzy]pub)(.*)/);
      if (match) {
        this.xpub = match[0];
        this.xpubKeyPrefix = match[1] as XpubPrefix;
      } else {
        this.xpub = this.edit.xpub;
      }

      this.derivationPath = this.edit.derivationPath;
    }
  }

  mounted() {
    this.setEditMode();
  }

  @Watch('address')
  onAddressChanged() {
    this.clearErrors(FIELD_ADDRESS);
  }

  @Watch('multiple')
  onMultiple() {
    this.addresses = '';
    this.address = '';
  }

  @Watch('edit')
  onEdit() {
    this.setEditMode();
  }

  @Watch('blockchain')
  onBlockchainChanged() {
    if (this.isBtc) {
      this.inputMode = XPUB_ADD;
    } else {
      this.inputMode = MANUAL_ADD;
    }
  }

  @Watch('xpub')
  onXpubChange(value: string) {
    if (!value) {
      return;
    }
    this.clearErrors(FIELD_XPUB);
    this.setXpubKeyType(value);
  }

  @Watch('derivationPath')
  onDerivationPathChange() {
    this.clearErrors(FIELD_DERIVATION_PATH);
  }

  private setXpubKeyType(value: string) {
    const match = AccountForm.isPrefixed(value);
    if (match && match.length === 3) {
      const prefix = match[1] as XpubPrefix;
      if (prefix === XPUB_VALUE) {
        return;
      }
      this.xpubKeyPrefix = prefix;
    }
  }

  private static isPrefixed(value: string) {
    return value.match(/([xzy]pub)(.*)/);
  }

  onPasteMulti(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.addresses += paste.replace(/,(0x)/g, ',\n0x');
    }
  }

  onPasteAddress(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.address = paste;
    }
  }

  onPasteXpub(event: ClipboardEvent) {
    const paste = trimOnPaste(event);
    if (paste) {
      this.setXpubKeyType(paste);
      this.xpub = paste;
    }
  }

  reset() {
    this.address = '';
    this.addresses = '';
    this.label = '';
    this.tags = [];
    this.xpub = '';
    this.derivationPath = '';
    (this.$refs.form as any).resetValidation();
    this.blockchain = ETH;
    this.inputMode = MANUAL_ADD;
    this.multiple = false;
  }

  @Emit()
  input(_valid: boolean) {}

  get accountOperation(): boolean {
    return (
      this.isTaskRunning(TaskType.ADD_ACCOUNT) ||
      this.isTaskRunning(TaskType.REMOVE_ACCOUNT) ||
      this.pending
    );
  }

  get loading(): boolean {
    return (
      this.isTaskRunning(TaskType.QUERY_BALANCES) ||
      this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)
    );
  }

  async metamaskImport(): Promise<boolean> {
    try {
      let addresses: string[];
      if (this.$interop.isPackaged) {
        addresses = await this.$interop.metamaskImport();
      } else {
        addresses = await getMetamaskAddresses();
      }

      const payload = addresses.map(value => ({
        address: value,
        label: this.label,
        tags: this.tags
      }));

      await this.addAccounts({
        blockchain: ETH,
        payload: payload,
        modules: this.selectedModules
      });
      return true;
    } catch (e) {
      const title = this.$tc('blockchain_balances.metamask_import.error.title');
      const description = this.$tc(
        'blockchain_balances.metamask_import.error.description',
        0,
        {
          error: e.message
        }
      );
      notify(description, title, Severity.ERROR, true);
      return false;
    }
  }

  payload(): BlockchainAccountPayload {
    let xpubPayload: XpubPayload | undefined;
    if (this.isBtc && this.isXpub) {
      const trimmedKey = this.xpub.trim();
      xpubPayload = {
        xpub: trimmedKey,
        derivationPath: this.derivationPath ?? undefined,
        xpubType: getKeyType(this.xpubKeyPrefix)
      };
    } else {
      xpubPayload = undefined;
    }

    return {
      blockchain: this.blockchain,
      address: this.address.trim(),
      label: this.label,
      tags: this.tags,
      xpub: xpubPayload,
      modules: this.isEth ? this.selectedModules : undefined
    };
  }

  async manualAdd() {
    try {
      if (this.edit) {
        await this.editAccount(this.payload());
      } else {
        if (this.entries.length > 0) {
          await this.addAccounts({
            blockchain: this.blockchain,
            payload: this.entries.map(address => ({
              address: address,
              label: this.label,
              tags: this.tags
            })),
            modules: this.isEth ? this.selectedModules : undefined
          } as AddAccountsPayload);
        } else {
          await this.addAccount(this.payload());
        }
      }

      this.reset();
    } catch (e) {
      const apiErrorMessage = deserializeApiErrorMessage(e.message);
      if (apiErrorMessage && Object.keys(apiErrorMessage).length > 0) {
        const errors: ValidationErrors = validationErrors();
        this.clearErrors(FIELD_ADDRESS);
        this.clearErrors(FIELD_XPUB);
        this.clearErrors(FIELD_DERIVATION_PATH);

        for (const field of FIELDS) {
          if (!(field in apiErrorMessage)) {
            continue;
          }

          errors[field] = errors[field].concat(apiErrorMessage[field]);
        }

        this.setErrors(FIELD_ADDRESS, errors[FIELD_ADDRESS]);
        this.setErrors(FIELD_XPUB, errors[FIELD_XPUB]);
        this.setErrors(FIELD_DERIVATION_PATH, errors[FIELD_DERIVATION_PATH]);
        this.pending = false;
        return false;
      }
      this.$store.commit('setMessage', {
        description: this.$tc('account_form.error.description', 0, {
          error: e.message
        }),
        title: this.$tc('account_form.error.title'),
        success: false
      } as Message);
      return false;
    }
    return true;
  }

  async save(): Promise<boolean> {
    let result: boolean;
    this.pending = true;

    if (this.isMetaMask) {
      result = await this.metamaskImport();
    } else {
      result = await this.manualAdd();
    }

    this.pending = false;
    return result;
  }

  private setErrors(field: ValidationFields, errors: string[]) {
    this.errorMessages[field].push(...errors);
    this.input(false);
  }

  private clearErrors(field: ValidationFields) {
    const errorMessages = this.errorMessages[field];
    if (errorMessages.length === 0) {
      return;
    }

    for (let i = 0; i < errorMessages.length; i++) {
      errorMessages.pop();
    }
    this.input(true);
  }
}
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
