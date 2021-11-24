<template>
  <v-row no-gutters class="mt-2">
    <v-col>
      <v-row v-if="multi" no-gutters align="center">
        <v-col cols="auto">
          <v-checkbox
            v-model="multiple"
            :disabled="disabled"
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
</template>

<script lang="ts">
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
import i18n from '@/i18n';
import { trimOnPaste } from '@/utils/event';

const setupValidationRules = () => {
  const nonEmptyRule = (value: string) => {
    return (
      !!value || i18n.t('account_form.validation.address_non_empty').toString()
    );
  };

  const rules = [nonEmptyRule];
  return { rules };
};

export default defineComponent({
  name: 'AddressInput',
  props: {
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
  },
  emits: ['update:addresses'],
  setup(props, { emit }) {
    const { errorMessages, addresses } = toRefs(props);
    const address = ref('');
    const userAddresses = ref('');
    const multiple = ref(false);
    const entries = computed(() => {
      const allAddresses = userAddresses.value
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
      userAddresses.value = '';
    });

    const onPasteMulti = (event: ClipboardEvent) => {
      const paste = trimOnPaste(event);
      if (paste) {
        userAddresses.value += paste.replace(/,(0x)/g, ',\n0x');
      }
    };

    const onPasteAddress = (event: ClipboardEvent) => {
      const paste = trimOnPaste(event);
      if (paste) {
        address.value = paste;
      }
    };

    const errors = computed(() => {
      const messages = unref(errorMessages);
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
        address.value = addresses[0];
      }
    };

    watch(addresses, addresses => setAddress(addresses));
    onMounted(() => setAddress(unref(addresses)));

    return {
      address,
      userAddresses,
      multiple,
      entries,
      errors,
      ...setupValidationRules(),
      onPasteMulti,
      onPasteAddress
    };
  }
});
</script>
