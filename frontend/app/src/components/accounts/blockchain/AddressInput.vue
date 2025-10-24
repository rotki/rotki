<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import useVuelidate from '@vuelidate/core';
import { helpers, requiredIf } from '@vuelidate/validators';
import { isEmpty } from 'es-toolkit/compat';
import WalletAddressesImport from '@/components/accounts/blockchain/WalletAddressesImport.vue';
import { trimOnPaste } from '@/utils/event';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  addresses: string[];
  disabled: boolean;
  multi: boolean;
  errorMessages: ValidationErrors;
  showWalletImport?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:addresses', addresses: string[]): void;
  (e: 'update:error-messages', errorMessages: ValidationErrors): void;
}>();

const { t } = useI18n({ useScope: 'global' });
const { addresses, disabled, errorMessages } = toRefs(props);

const address = ref<string>('');
const userAddresses = ref<string>('');
const multiple = ref<boolean>(false);

const entries = computed(() => {
  const allAddresses = get(userAddresses)
    .split(/[\n,]+/)
    .map(value => value.trim())
    .filter(entry => entry.length > 0);

  const entries: Record<string, string> = {};
  for (const address of allAddresses) {
    const lowerCase = address.toLocaleLowerCase();
    if (entries[lowerCase])
      continue;

    entries[lowerCase] = address;
  }
  return Object.values(entries);
});

function onPasteMulti(event: ClipboardEvent) {
  if (get(disabled))
    return;

  const paste = trimOnPaste(event);
  if (paste)
    userAddresses.value += paste.replace(/,(0x)/g, ',\n0x');
}

function onPasteAddress(event: ClipboardEvent) {
  if (get(disabled))
    return;

  const paste = trimOnPaste(event);
  if (paste)
    set(address, paste);
}

function updateErrorMessages(errorMessages: ValidationErrors) {
  emit('update:error-messages', errorMessages);
}

watch(entries, addresses => updateAddresses(addresses));
watch(address, (address) => {
  updateAddresses(address ? [address.trim()] : []);
});

function setAddress(addresses: string[]) {
  if (addresses.length === 1) {
    set(address, addresses[0]);
  }
  else if (addresses.length === 0) {
    set(address, '');
    set(userAddresses, '');
  }
}

watch(addresses, addresses => setAddress(addresses));
onMounted(() => setAddress(get(addresses)));

const rules = {
  address: {
    required: helpers.withMessage(
      t('account_form.validation.address_non_empty'),
      requiredIf(logicNot(multiple)),
    ),
  },
  userAddresses: {
    required: helpers.withMessage(
      t('account_form.validation.address_non_empty'),
      requiredIf(logicAnd(multiple)),
    ),
  },
};

const errorMessagesModel = computed({
  get() {
    const errors = get(errorMessages);
    return {
      address: errors.address || '',
      userAddresses: errors.address || '',
    };
  },
  set(newErrors) {
    const error = newErrors.address;
    if (error) {
      updateErrorMessages({
        address: error,
      });
    }
    else {
      updateErrorMessages({});
    }
  },
});

const v$ = useVuelidate(
  rules,
  {
    address,
    userAddresses,
  },
  {
    $autoDirty: true,
    $externalResults: errorMessagesModel,
    $stopPropagation: true,
  },
);

function updateAddresses(addresses: string[]) {
  get(v$).$clearExternalResults();
  emit('update:addresses', addresses);
}

function validate(): Promise<boolean> {
  return get(v$).$validate();
}

watch(errorMessages, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

watch(multiple, () => {
  get(v$).$clearExternalResults();
  set(userAddresses, '');
});

function updateAddressesFromWalletImport(addresses: string[]) {
  if (addresses.length > 1) {
    set(multiple, true);
    nextTick(() => {
      set(userAddresses, addresses.join(',\n'));
    });
  }
  else if (addresses.length === 1) {
    set(multiple, false);
    nextTick(() => {
      set(address, addresses[0]);
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
      v-if="multi"
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
        v-model="address"
        data-cy="account-address-field"
        variant="outlined"
        color="primary"
        class="account-form__address flex-1"
        :label="t('common.account')"
        :rules="rules"
        autocomplete="off"
        :disabled="disabled"
        :error-messages="toMessages(v$.address)"
        @paste="onPasteAddress($event)"
        @blur="v$.address.$touch()"
      />
      <RuiTextArea
        v-else
        v-model="userAddresses"
        variant="outlined"
        color="primary"
        class="flex-1"
        min-rows="5"
        :disabled="disabled"
        :error-messages="toMessages(v$.userAddresses)"
        :hint="t('account_form.labels.addresses_hint')"
        :label="t('account_form.labels.addresses')"
        @blur="v$.userAddresses.$touch()"
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
