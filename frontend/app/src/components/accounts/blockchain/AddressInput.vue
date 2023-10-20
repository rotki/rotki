<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    addresses: string[];
    disabled: boolean;
    multi: boolean;
    errorMessages?: string[];
  }>(),
  {
    errorMessages: () => []
  }
);

const emit = defineEmits<{
  (e: 'update:addresses', addresses: string[]): void;
}>();

const { t } = useI18n();
const { errorMessages, addresses, disabled } = toRefs(props);
const address = ref('');
const userAddresses = ref('');
const multiple = ref(false);
const entries = computed(() => {
  const allAddresses = get(userAddresses)
    .split(',')
    .map(value => value.trim())
    .filter(entry => entry.length > 0);

  const entries: Record<string, string> = {};
  for (const address of allAddresses) {
    const lowerCase = address.toLocaleLowerCase();
    if (entries[lowerCase]) {
      continue;
    }
    entries[lowerCase] = address;
  }
  return Object.values(entries);
});

watch(multiple, () => {
  set(userAddresses, '');
});

const onPasteMulti = (event: ClipboardEvent) => {
  if (get(disabled)) {
    return;
  }
  const paste = trimOnPaste(event);
  if (paste) {
    userAddresses.value += paste.replace(/,(0x)/g, ',\n0x');
  }
};

const onPasteAddress = (event: ClipboardEvent) => {
  if (get(disabled)) {
    return;
  }
  const paste = trimOnPaste(event);
  if (paste) {
    set(address, paste);
  }
};

const updateAddresses = (addresses: string[]) => {
  emit('update:addresses', addresses);
};

watch(entries, addresses => updateAddresses(addresses));
watch(address, address => {
  updateAddresses(address ? [address.trim()] : []);
});

const setAddress = (addresses: string[]) => {
  if (addresses.length === 1) {
    set(address, addresses[0]);
  }
};

watch(addresses, addresses => setAddress(addresses));
onMounted(() => setAddress(get(addresses)));

const rules = [
  (v: string) =>
    !!v || t('account_form.validation.address_non_empty').toString()
];
</script>

<template>
  <div>
    <RuiCheckbox
      v-if="multi"
      v-model="multiple"
      color="primary"
      class="mt-0 mb-6"
      hide-details
      :disabled="disabled"
    >
      {{ t('account_form.labels.multiple') }}
    </RuiCheckbox>
    <VTextField
      v-if="!multiple"
      v-model="address"
      data-cy="account-address-field"
      outlined
      class="account-form__address"
      :label="t('common.account')"
      :rules="rules"
      :error-messages="errorMessages"
      autocomplete="off"
      :disabled="disabled"
      @paste="onPasteAddress($event)"
    />
    <VTextarea
      v-else
      v-model="userAddresses"
      outlined
      :disabled="disabled"
      :error-messages="errorMessages"
      :hint="t('account_form.labels.addresses_hint')"
      :label="t('account_form.labels.addresses')"
      @paste="onPasteMulti($event)"
    />
    <div v-if="multiple">
      <div
        class="text-caption mb-2"
        v-text="
          t(
            'account_form.labels.addresses_entries',
            {
              count: entries.length
            },
            entries.length
          )
        "
      />
    </div>
  </div>
</template>
