<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { SelectOption, SelectOptions } from '@/types/common';
import AssetIconForm from '@/components/asset-manager/AssetIconForm.vue';
import UnderlyingTokenManager from '@/components/asset-manager/UnderlyingTokenManager.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import HelpLink from '@/components/helper/HelpLink.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useAssetManagementApi } from '@/composables/api/assets/management';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useFormStateWatcher } from '@/composables/form';
import { useSupportedChains } from '@/composables/info/chains';
import { useMessageStore } from '@/store/message';
import { CUSTOM_ASSET, EVM_TOKEN } from '@/types/asset';
import { evmTokenKindsData } from '@/types/blockchain/chains';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { refOptional, useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import { isValidEthAddress, onlyIfTruthy, type SupportedAsset, toSentenceCase, type UnderlyingToken } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { omit, pick } from 'es-toolkit';

const modelValue = defineModel<SupportedAsset>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = withDefaults(defineProps<{
  editMode?: boolean;
  loading?: boolean;
}>(), {
  editMode: false,
  loading: false,
});

const types = ref<SelectOptions>([{ key: EVM_TOKEN, label: toSentenceCase(EVM_TOKEN) }]);
const fetching = ref<boolean>(false);
const dontAutoFetch = ref<boolean>(false);
const underlyingTokens = ref<UnderlyingToken[]>([]);
const assetIconFormRef = ref<InstanceType<typeof AssetIconForm> | null>(null);

const identifier = useRefPropVModel(modelValue, 'identifier');
const address = refOptional(useRefPropVModel(modelValue, 'address'), '');
const name = refOptional(useRefPropVModel(modelValue, 'name'), '');
const symbol = refOptional(useRefPropVModel(modelValue, 'symbol'), '');
const decimals = useRefPropVModel(modelValue, 'decimals');
const coingecko = refOptional(useRefPropVModel(modelValue, 'coingecko'), '');
const cryptocompare = refOptional(useRefPropVModel(modelValue, 'cryptocompare'), '');
const assetType = useRefPropVModel(modelValue, 'assetType');
const evmChain = useRefPropVModel(modelValue, 'evmChain');
const tokenKind = useRefPropVModel(modelValue, 'tokenKind');
const protocol = refOptional(useRefPropVModel(modelValue, 'protocol'), '');
const swappedFor = refOptional(useRefPropVModel(modelValue, 'swappedFor'), '');
const forked = refOptional(useRefPropVModel(modelValue, 'forked'), '');
const started = useRefPropVModel(modelValue, 'started');

const startedModel = computed({
  get: () => {
    const startedVal = get(started);
    return startedVal ? convertFromTimestamp(startedVal) : '';
  },
  set: (value?: string) => {
    set(started, value ? convertToTimestamp(value) : undefined);
  },
});

const decimalsModel = computed({
  get() {
    return `${get(decimals)}`;
  },
  set(value: string) {
    set(decimals, parseDecimals(value));
  },
});

const { setMessage } = useMessageStore();
const { t } = useI18n({ useScope: 'global' });
const { allEvmChains, txEvmChains } = useSupportedChains();
const { fetchTokenDetails } = useAssetInfoRetrieval();
const { addAsset, editAsset, getAssetTypes } = useAssetManagementApi();

const isEvmToken = computed<boolean>(() => get(assetType) === EVM_TOKEN);
const externalServerValidation = () => true;

const states = {
  address,
  assetType,
  coingecko,
  cryptocompare,
  decimals,
  evmChain,
  forked,
  name,
  protocol,
  started,
  swappedFor,
  symbol,
  tokenKind,
};

const v$ = useVuelidate({
  address: {
    required: requiredIf(isEvmToken),
    validated: helpers.withMessage(
      t('asset_form.validation.valid_address'),
      (v: string) => !get(isEvmToken) || isValidEthAddress(v),
    ),
  },
  assetType: { required },
  coingecko: { externalServerValidation },
  cryptocompare: { externalServerValidation },
  decimals: { externalServerValidation },
  evmChain: { externalServerValidation },
  forked: { externalServerValidation },
  name: { externalServerValidation },
  protocol: { externalServerValidation },
  started: { externalServerValidation },
  swappedFor: { externalServerValidation },
  symbol: { externalServerValidation },
  tokenKind: { externalServerValidation },
}, states, { $autoDirty: true, $externalResults: errors });

useFormStateWatcher(states, stateUpdated);

function parseDecimals(value?: string): number | null {
  if (!value)
    return null;

  const parsedValue = Number.parseInt(value);
  return Number.isNaN(parsedValue) ? null : parsedValue;
}

function clearFieldError(field: keyof SupportedAsset) {
  set(errors, omit(get(errors), [field]));
}

function clearFieldErrors(fields: Array<keyof SupportedAsset>) {
  fields.forEach(clearFieldError);
}

async function saveAsset() {
  let newIdentifier: string;
  const data = get(modelValue);

  const payload: SupportedAsset = omit({
    ...data,
    coingecko: get(coingecko),
    cryptocompare: get(cryptocompare),
    evmChain: get(evmChain) || null,
    protocol: onlyIfTruthy(get(protocol)),
    swappedFor: onlyIfTruthy(get(swappedFor)),
    tokenKind: get(tokenKind) || null,
    underlyingTokens: get(underlyingTokens).length > 0 ? get(underlyingTokens) : undefined,
  }, ['ended', 'active', 'customAssetType']);

  const assetPayload = get(isEvmToken)
    ? payload
    : omit(payload, ['decimals', 'address', 'evmChain', 'tokenKind', 'underlyingTokens']);

  if (props.editMode) {
    newIdentifier = get(identifier);
    await editAsset({ ...assetPayload, identifier: newIdentifier });
  }
  else {
    ({ identifier: newIdentifier } = await addAsset(omit(assetPayload, ['identifier'])));
  }
  return newIdentifier;
}

function saveIcon(identifier: string) {
  get(assetIconFormRef)?.saveIcon(identifier);
}

async function fetchTokenData(address: string, evmChain: string): Promise<void> {
  if (!isValidEvmChain(evmChain)) {
    return;
  }
  set(fetching, true);

  const tokenInfo = pick(get(modelValue), ['decimals', 'name', 'symbol']);
  const tokenDetails = await fetchTokenDetails({ address, evmChain });

  const updateTokenInfo = {
    decimals: tokenDetails.decimals ? tokenDetails.decimals : tokenInfo.decimals,
    name: tokenDetails.name ? tokenDetails.name : tokenInfo.name,
    symbol: tokenDetails.symbol ? tokenDetails.symbol : tokenInfo.symbol,
  };

  set(modelValue, { ...get(modelValue), ...updateTokenInfo });

  set(fetching, false);
  clearFieldErrors(['decimals', 'name', 'symbol']);
}

async function refreshTokenData() {
  if (!isDefined(evmChain)) {
    return;
  }

  await fetchTokenData(get(address), get(evmChain));
}

function isValidEvmChain(evmChain: string) {
  return get(txEvmChains).some(({ evmChainName }) => evmChainName === evmChain);
}

watch([address, evmChain], async ([address, evmChain]) => {
  if (!evmChain)
    return;

  if (get(dontAutoFetch) || !isValidEthAddress(address)) {
    set(dontAutoFetch, false);
    return;
  }

  await fetchTokenData(address, evmChain);
});

watch(assetType, () => {
  // clearing errors because the errors are unique based on the asset type
  set(errors, {});
});

watchImmediate(modelValue, (asset) => {
  if (asset.underlyingTokens && asset.underlyingTokens.length > 0) {
    set(underlyingTokens, asset.underlyingTokens);
  }
  else {
    set(underlyingTokens, []);
  }
});

onBeforeMount(async () => {
  try {
    const queriedTypes = await getAssetTypes();
    set(
      types,
      queriedTypes
        .filter(item => item !== CUSTOM_ASSET)
        .map<SelectOption>(item => ({ key: item, label: toSentenceCase(item) })),
    );
  }
  catch (error: any) {
    setMessage({
      description: t('asset_form.types.error', {
        message: error.message,
      }),
    });
  }
});

onMounted(() => {
  set(dontAutoFetch, props.editMode);
});

defineExpose({
  saveAsset,
  saveIcon,
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <div class="flex flex-col gap-3">
    <div
      v-if="editMode"
      class="flex items-center text-caption text-rui-text-secondary -mt-2 mb-4 gap-2"
    >
      <span class="font-medium"> {{ t('asset_form.identifier') }}: </span>
      <div class="flex items-center">
        {{ identifier }}
        <CopyButton
          class="ml-2"
          size="sm"
          :value="identifier"
          :tooltip="t('asset_form.identifier_copy')"
        />
      </div>
    </div>
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-3">
      <div
        class="col-span-2"
        data-cy="type-select"
      >
        <RuiMenuSelect
          v-model="assetType"
          :label="t('asset_form.labels.asset_type')"
          :options="types"
          :disabled="types.length === 1 || editMode"
          :error-messages="toMessages(v$.assetType)"
          key-attr="key"
          text-attr="label"
          variant="outlined"
        />
      </div>

      <template v-if="isEvmToken">
        <div data-cy="chain-select">
          <RuiMenuSelect
            v-model="evmChain"
            :label="t('asset_form.labels.chain')"
            :options="allEvmChains"
            :disabled="editMode"
            :error-messages="toMessages(v$.evmChain)"
            key-attr="name"
            text-attr="label"
            variant="outlined"
          />
        </div>

        <div data-cy="token-select">
          <RuiMenuSelect
            v-model="tokenKind"
            :label="t('asset_form.labels.token_kind')"
            :options="evmTokenKindsData"
            :disabled="editMode"
            :error-messages="toMessages(v$.tokenKind)"
            key-attr="identifier"
            text-attr="label"
            variant="outlined"
          />
        </div>
        <div
          class="col-span-2"
          data-cy="address-input"
        >
          <RuiTextField
            v-model="address"
            variant="outlined"
            color="primary"
            :loading="fetching"
            :error-messages="toMessages(v$.address)"
            :label="t('common.address')"
            :disabled="loading || fetching || editMode"
            @keydown.space.
            @blur="v$.address.$touch()"
          >
            <template
              v-if="isEvmToken && editMode"
              #append
            >
              <RuiButton
                variant="text"
                icon
                :disabled="loading || fetching"
                @click="refreshTokenData()"
              >
                <RuiIcon name="lu-refresh-cw" />
              </RuiButton>
            </template>
          </RuiTextField>
        </div>
      </template>

      <div class="col-span-2 grid md:grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-3">
        <RuiTextField
          v-model="name"
          data-cy="name-input"
          class="md:col-span-2"
          variant="outlined"
          color="primary"
          :error-messages="toMessages(v$.name)"
          :label="t('common.name')"
          :disabled="loading || fetching"
          @blur="v$.name.$touch()"
        />

        <RuiTextField
          v-model="symbol"
          :class="isEvmToken ? 'md:col-span-1' : 'md:col-span-2'"
          data-cy="symbol-input"
          variant="outlined"
          color="primary"
          :error-messages="toMessages(v$.symbol)"
          :label="t('asset_form.labels.symbol')"
          :disabled="loading || fetching"
          @blur="v$.symbol.$touch()"
        />
        <div
          v-if="isEvmToken"
          data-cy="decimal-input"
        >
          <RuiTextField
            v-model="decimalsModel"
            variant="outlined"
            color="primary"
            min="0"
            max="18"
            type="number"
            :label="t('asset_form.labels.decimals')"
            :error-messages="toMessages(v$.decimals)"
            :disabled="loading || fetching"
            @blur="v$.decimals.$touch()"
          />
        </div>
        <RuiTextField
          v-model="coingecko"
          variant="outlined"
          color="primary"
          clearable
          class="col-span-2"
          :hint="t('asset_form.labels.coingecko_hint')"
          :label="t('asset_form.labels.coingecko')"
          :error-messages="toMessages(v$.coingecko)"
          :disabled="loading"
          @blur="v$.coingecko.$touch()"
        >
          <template #append>
            <HelpLink
              small
              :url="externalLinks.contributeSection.coingecko"
              :tooltip="t('asset_form.help_coingecko')"
            />
          </template>
        </RuiTextField>
        <RuiTextField
          v-model="cryptocompare"
          variant="outlined"
          color="primary"
          clearable
          class="col-span-2"
          :label="t('asset_form.labels.cryptocompare')"
          :hint="t('asset_form.labels.cryptocompare_hint')"
          :error-messages="toMessages(v$.cryptocompare)"
          :disabled="loading"
          @blur="v$.cryptocompare.$touch()"
        >
          <template #append>
            <HelpLink
              small
              :url="externalLinks.contributeSection.cryptocompare"
              :tooltip="t('asset_form.help_cryptocompare')"
            />
          </template>
        </RuiTextField>
      </div>
    </div>

    <RuiCard
      no-padding
      rounded="sm"
      class="col-span-2 mt-2 mb-4 overflow-hidden"
    >
      <RuiAccordions>
        <RuiAccordion
          header-grow
          header-class="p-4"
        >
          <template #header>
            {{ t('asset_form.optional') }}
          </template>
          <template #default>
            <div class="p-4">
              <DateTimePicker
                v-model="startedModel"
                :label="t('asset_form.labels.started')"
                :error-messages="toMessages(v$.started)"
                :disabled="loading"
              />
              <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
                <RuiTextField
                  v-if="isEvmToken"
                  v-model="protocol"
                  variant="outlined"
                  color="primary"
                  clearable
                  class="asset-form__protocol"
                  :label="t('common.protocol')"
                  :error-messages="toMessages(v$.protocol)"
                  :disabled="loading"
                  @blur="v$.protocol.$touch()"
                />
                <AssetSelect
                  v-model="swappedFor"
                  outlined
                  clearable
                  :label="t('asset_form.labels.swapped_for')"
                  :error-messages="toMessages(v$.swappedFor)"
                  :disabled="loading"
                />
                <AssetSelect
                  v-if="!isEvmToken && assetType"
                  v-model="forked"
                  outlined
                  clearable
                  :label="t('asset_form.labels.forked')"
                  :error-messages="toMessages(v$.forked)"
                  :disabled="loading"
                />
              </div>
              <UnderlyingTokenManager
                v-if="isEvmToken"
                v-model="underlyingTokens"
                class="border-t border-default pt-6 mt-2"
              />
            </div>
          </template>
        </RuiAccordion>
      </RuiAccordions>
    </RuiCard>

    <AssetIconForm
      ref="assetIconFormRef"
      class="col-span-2"
      :identifier="identifier"
      refreshable
    />
  </div>
</template>
