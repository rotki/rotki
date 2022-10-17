<template>
  <v-row no-gutters class="mt-2">
    <v-col>
      <v-row v-if="multi" no-gutters align="center">
        <v-col cols="auto">
          <v-checkbox
            v-model="multiple"
            :disabled="disabled"
            :label="t('account_form.labels.multiple')"
          />
        </v-col>
      </v-row>
      <v-text-field
        v-if="!multiple"
        v-model="address"
        data-cy="account-address-field"
        outlined
        class="account-form__address"
        :label="t('common.account')"
        :rules="rules"
        :error-messages="errors"
        autocomplete="off"
        :disabled="disabled"
        @paste="onPasteAddress"
      />
      <v-textarea
        v-else
        v-model="userAddresses"
        outlined
        :disabled="disabled"
        :error-messages="errors"
        :hint="t('account_form.labels.addresses_hint')"
        :label="t('account_form.labels.addresses')"
        @paste="onPasteMulti"
      />
      <v-row v-if="multiple" no-gutters>
        <v-col>
          <div
            class="text-caption"
            v-text="
              tc('account_form.labels.addresses_entries', entries.length, {
                count: entries.length
              })
            "
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { trimOnPaste } from '@/utils/event';

const props = defineProps({
  addresses: {
    required: true,
    type: Array as PropType<string[]>
  },
  disabled: {
    required: true,
    type: Boolean
  },
  multi: {
    required: true,
    type: Boolean
  },
  errorMessages: {
    required: true,
    type: Object as PropType<Record<string, string[]>>
  }
});

const emit = defineEmits(['update:addresses']);

const { t, tc } = useI18n();
const { errorMessages, addresses, disabled } = toRefs(props);
const address = ref('');
const userAddresses = ref('');
const multiple = ref(false);
const entries = computed(() => {
  const allAddresses = get(userAddresses)
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

watch(multiple, () => {
  set(userAddresses, '');
});

const onPasteMulti = (event: ClipboardEvent) => {
  if (get(disabled)) return;
  const paste = trimOnPaste(event);
  if (paste) {
    userAddresses.value += paste.replace(/,(0x)/g, ',\n0x');
  }
};

const onPasteAddress = (event: ClipboardEvent) => {
  if (get(disabled)) return;
  const paste = trimOnPaste(event);
  if (paste) {
    set(address, paste);
  }
};

const errors = computed(() => {
  const messages = get(errorMessages);
  return messages['address'];
});

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
  (v: string) => {
    return !!v || t('account_form.validation.address_non_empty').toString();
  }
];
</script>
