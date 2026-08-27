<script setup lang="ts">
import type { ZodType } from 'zod';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import {
  addressEntrySchema,
  type AddressFormState,
  isXpubPrefix,
  parseAddressEntries,
  replaceSelection,
} from '@/modules/accounts/blockchain/address-entries';
import WalletAddressesImport from '@/modules/accounts/blockchain/WalletAddressesImport.vue';
import { trimOnPaste } from '@/modules/core/common/helpers/event';
import { toServerErrors } from '@/modules/core/form/server-errors';
import { noSubmit, useForm } from '@/modules/core/form/use-form';

const addresses = defineModel<string[]>('addresses', { required: true });
const errorMessages = defineModel<ValidationErrors>('errorMessages', { required: true });

const { disabled, multi, showWalletImport, forceMultiple = false } = defineProps<{
  disabled: boolean;
  multi: boolean;
  showWalletImport?: boolean;
  forceMultiple?: boolean;
}>();

const emit = defineEmits<{
  'detected-xpub': [key: string];
}>();

const { t } = useI18n({ useScope: 'global' });

const multiple = ref<boolean>(forceMultiple);

const schema = computed<ZodType>(() => addressEntrySchema(
  t('account_form.validation.address_non_empty'),
  get(multiple),
));

const { errors: fieldErrors, setServerErrors, state, touch, validate } = useForm<AddressFormState, AddressFormState>({
  initial: (): AddressFormState => ({ address: '', userAddresses: '' }),
  schema,
  submit: noSubmit,
  transform: (state): AddressFormState => ({ ...state }),
});

const entries = computed<string[]>(() => parseAddressEntries(state.userAddresses));

function onPasteMulti(event: ClipboardEvent): void {
  if (disabled)
    return;

  const paste = trimOnPaste(event);
  if (!paste)
    return;

  const trimmed = paste.trim();
  if (isXpubPrefix(trimmed)) {
    emit('detected-xpub', trimmed);
    return;
  }

  const { target } = event;
  const current = state.userAddresses;
  const replacement = paste.replace(/,(0x)/g, ',\n0x');

  state.userAddresses = target instanceof HTMLTextAreaElement && target.selectionStart !== target.selectionEnd
    ? replaceSelection(current, replacement, target.selectionStart, target.selectionEnd)
    : current + replacement;
}

function onPasteAddress(event: ClipboardEvent): void {
  if (disabled)
    return;

  const paste = trimOnPaste(event);
  if (!paste)
    return;

  const trimmed = paste.trim();
  if (isXpubPrefix(trimmed)) {
    emit('detected-xpub', trimmed);
    return;
  }

  state.address = paste;
}

/**
 * An edit answers whatever the backend last said about the addresses, so the errors the parent is
 * holding go with it. The core drops the message under the field on its own; this is what stops a
 * stale one being handed back to the next form the dialog opens.
 */
function updateAddresses(newAddresses: string[]): void {
  set(errorMessages, {});
  set(addresses, newAddresses);
}

function setAddress(addresses: string[]): void {
  if (addresses.length === 1) {
    if (get(multiple)) {
      if (!state.userAddresses)
        state.userAddresses = addresses[0];
    }
    else {
      state.address = addresses[0];
    }
  }
  else if (addresses.length === 0) {
    state.address = '';
    state.userAddresses = '';
  }
}

/**
 * Shows the backend's address error against both the single and the multiple field.
 *
 * @remarks
 * The backend reports one flat `address` key whichever mode the form is in, so the message is put
 * on both rather than keyed to the one the state happens to call it. Only one is ever on screen.
 */
function mirrorAddressErrorAcrossModes(value: ValidationErrors): void {
  const messages = toServerErrors(value).address ?? [];
  setServerErrors({ address: messages, userAddresses: messages });
}

watchImmediate(errorMessages, mirrorAddressErrorAcrossModes, { deep: true });

watch(entries, addresses => updateAddresses(addresses));

watch(() => state.address, (address) => {
  updateAddresses(address ? [address.trim()] : []);
});

watch(addresses, addresses => setAddress(addresses));
onMounted(() => setAddress(get(addresses)));

watch(multiple, () => {
  set(errorMessages, {});
  state.userAddresses = '';
});

/** Waits a tick, because switching mode empties the field the imported addresses are written to. */
function updateAddressesFromWalletImport(addresses: string[]): void {
  if (addresses.length > 1) {
    set(multiple, true);
    nextTick(() => {
      state.userAddresses = addresses.join(',\n');
    });
  }
  else if (addresses.length === 1) {
    set(multiple, false);
    nextTick(() => {
      state.address = addresses[0];
    });
  }
}

defineExpose({
  validate,
});
</script>

<template>
  <div>
    <RuiCheckbox
      v-if="multi && !forceMultiple"
      v-model="multiple"
      color="primary"
      class="mt-0 mb-4 flex"
      hide-details
      :disabled="disabled"
    >
      {{ t('account_form.labels.multiple') }}
    </RuiCheckbox>
    <div class="flex items-start gap-2">
      <RuiTextField
        v-if="!multiple"
        v-model="state.address"
        data-testid="account-address-field"
        variant="outlined"
        color="primary"
        class="flex-1"
        :label="t('common.account')"
        autocomplete="off"
        :disabled="disabled"
        :error-messages="fieldErrors('address')"
        @paste="onPasteAddress($event)"
        @update:model-value="touch('address')"
      />
      <RuiTextArea
        v-else
        v-model="state.userAddresses"
        data-testid="account-address-field"
        variant="outlined"
        color="primary"
        class="flex-1"
        :min-rows="forceMultiple ? (entries.length > 1 ? 4 : 2) : 5"
        :disabled="disabled"
        :error-messages="fieldErrors('userAddresses')"
        :hint="t('account_form.labels.addresses_hint')"
        :placeholder="forceMultiple ? t('account_form.labels.btc.placeholder') : undefined"
        :label="forceMultiple ? t('account_form.labels.btc.addresses') : t('account_form.labels.addresses')"
        @update:model-value="touch('userAddresses')"
        @paste="onPasteMulti($event)"
      />
      <WalletAddressesImport
        v-if="showWalletImport"
        :disabled="disabled"
        @update:addresses="updateAddressesFromWalletImport($event)"
      />
    </div>

    <div
      v-if="multiple"
      class="text-caption mb-2 px-3"
      v-text="
        t(
          'account_form.labels.addresses_entries',
          {
            count: entries.length,
          },
          entries.length,
        )
      "
    />
  </div>
</template>
