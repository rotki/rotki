<script setup lang="ts">
import { each } from 'lodash-es';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { toSentenceCase } from '@/utils/text';
import { toMessages } from '@/utils/validation';
import type {
  AddressBookLocation,
  AddressBookPayload,
} from '@/types/eth-names';

const props = withDefaults(
  defineProps<{
    value: AddressBookPayload;
    edit: boolean;
    enableForAllChains?: boolean;
    errorMessages: { address?: string[]; name?: string[] };
  }>(),
  {
    enableForAllChains: false,
  },
);

const emit = defineEmits<{
  (e: 'input', value: AddressBookPayload): void;
  (e: 'valid', valid: boolean): void;
  (e: 'update:enable-for-all-chains', enable: boolean): void;
}>();

const { t } = useI18n();
const { errorMessages } = toRefs(props);

const name = useSimplePropVModel(props, 'name', emit);
const address = useSimplePropVModel(props, 'address', emit);
const location = useSimplePropVModel(props, 'location', emit);
const blockchain = useSimplePropVModel(props, 'blockchain', emit);
const enabledForAllChains = useKebabVModel(props, 'enableForAllChains', emit);

const { btcAddresses, bchAddresses } = storeToRefs(useBtcAccountsStore());
const { ethAddresses } = storeToRefs(useEthAccountsStore());
const {
  ksmAddresses,
  dotAddresses,
  avaxAddresses,
  optimismAddresses,
  polygonAddresses,
  arbitrumAddresses,
  baseAddresses,
  gnosisAddresses,
  scrollAddresses,
} = storeToRefs(useChainsAccountsStore());
const addressesNamesStore = useAddressesNamesStore();
const { getAddressesWithoutNames, addressNameSelector } = addressesNamesStore;

const addresses = computed<Record<string, string[]>>(() => ({
  [Blockchain.BTC]: get(btcAddresses),
  [Blockchain.BCH]: get(bchAddresses),
  [Blockchain.ETH]: get(ethAddresses),
  [Blockchain.KSM]: get(ksmAddresses),
  [Blockchain.DOT]: get(dotAddresses),
  [Blockchain.AVAX]: get(avaxAddresses),
  [Blockchain.OPTIMISM]: get(optimismAddresses),
  [Blockchain.POLYGON_POS]: get(polygonAddresses),
  [Blockchain.ARBITRUM_ONE]: get(arbitrumAddresses),
  [Blockchain.BASE]: get(baseAddresses),
  [Blockchain.GNOSIS]: get(gnosisAddresses),
  [Blockchain.SCROLL]: get(scrollAddresses),
}));

const addressSuggestions = getAddressesWithoutNames(blockchain);
const locations: AddressBookLocation[] = ['global', 'private'];

const rules = {
  blockchain: {
    required: helpers.withMessage(
      t('address_book.form.validation.chain'),
      requiredIf(logicNot(enabledForAllChains)),
    ),
  },
  address: {
    required: helpers.withMessage(
      t('address_book.form.validation.address'),
      required,
    ),
  },
  name: {
    required: helpers.withMessage(
      t('address_book.form.validation.name'),
      required,
    ),
  },
};

const { setValidation } = useAddressBookForm();

const v$ = setValidation(
  rules,
  {
    blockchain,
    address,
    name,
  },
  { $autoDirty: true, $externalResults: errorMessages },
);

const { getBlockie } = useBlockie();

function fetchNames() {
  const addressMap = get(addresses);

  each(Blockchain, (chain) => {
    addressMap[chain]?.forEach(address => get(addressNameSelector(address, chain)));
  });
}

/**
 * if new suggestions does not include last suggested and selected address, reset address
 */
watch(addressSuggestions, (suggestions, oldSuggestions) => {
  const chainAddress = get(address);
  if (get(blockchain) && oldSuggestions.includes(chainAddress) && !suggestions.includes(chainAddress))
    set(address, '');
});

watchEffect(fetchNames);
onMounted(fetchNames);
</script>

<template>
  <form>
    <VSelect
      v-model="location"
      outlined
      :label="t('common.location')"
      :items="locations"
      :disabled="edit"
    >
      <template #item="{ item }">
        {{ toSentenceCase(item) }}
      </template>
      <template #selection="{ item }">
        {{ toSentenceCase(item) }}
      </template>
    </VSelect>
    <RuiSwitch
      v-model="enabledForAllChains"
      :disabled="edit"
      color="primary"
      :label="t('address_book.form.labels.for_all_chain')"
    />
    <ChainSelect
      :model-value.sync="blockchain"
      :disabled="edit || enabledForAllChains"
      exclude-eth-staking
      :error-messages="toMessages(v$.blockchain)"
    />
    <ComboboxWithCustomInput
      v-model.trim="address"
      outlined
      :label="t('address_book.form.labels.address')"
      :items="addressSuggestions"
      :no-data-text="t('address_book.form.no_suggestions_available')"
      :disabled="edit"
      :error-messages="toMessages(v$.address)"
      auto-select-first
      clearable
    >
      <template #prepend-inner>
        <div
          class="mr-2 rounded-full overflow-hidden w-6 h-6 bg-rui-grey-300 dark:bg-rui-grey-600"
        >
          <AppImage
            :src="getBlockie(value.address)"
            size="1.5rem"
          />
        </div>
      </template>
      <template #item="{ item }">
        <span v-if="item">
          <div
            class="mr-2 rounded-full overflow-hidden w-6 h-6 bg-rui-grey-300 dark:bg-rui-grey-600"
          >
            <AppImage
              :src="getBlockie(item)"
              size="1.5rem"
            />
          </div>
        </span>
        {{ item }}
      </template>
    </ComboboxWithCustomInput>
    <RuiTextField
      v-model="name"
      class="mt-2"
      variant="outlined"
      color="primary"
      :label="t('common.name')"
      :error-messages="toMessages(v$.name)"
    />
  </form>
</template>
