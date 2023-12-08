<script setup lang="ts">
import { onlyIfTruthy } from '@rotki/common';
import {
  type EvmTokenKind,
  type SupportedAsset,
  type UnderlyingToken
} from '@rotki/common/lib/data';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { omit } from 'lodash-es';
import { type ComputedRef, type Ref } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { toSentenceCase } from '@/utils/text';
import { evmTokenKindsData } from '@/types/blockchain/chains';
import { CUSTOM_ASSET, EVM_TOKEN } from '@/types/asset';
import { ApiValidationError } from '@/types/api/errors';
import AssetIconForm from '@/components/asset-manager/AssetIconForm.vue';
import { toMessages } from '@/utils/validation';

const props = withDefaults(
  defineProps<{
    editableItem?: SupportedAsset | null;
  }>(),
  {
    editableItem: null
  }
);

function time(t: string): number | undefined {
  return t ? convertToTimestamp(t) : undefined;
}

const { t } = useI18n();
const { editableItem } = toRefs(props);
const { fetchTokenDetails } = useAssetInfoRetrieval();

const address = ref<string>('');
const name = ref<string>('');
const symbol = ref<string>('');
const decimals = ref<string>();
const started = ref<string>('');
const coingecko = ref<string>('');
const cryptocompare = ref<string>('');
const assetType = ref<string>(EVM_TOKEN);
const evmChain = ref<string>();
const tokenKind = ref<string>();
const types = ref<string[]>([EVM_TOKEN]);
const identifier = ref<string>('');
const protocol = ref<string>('');
const swappedFor = ref<string>('');
const forked = ref<string>('');
const coingeckoEnabled = ref<boolean>(false);
const cryptocompareEnabled = ref<boolean>(false);
const fetching = ref<boolean>(false);
const dontAutoFetch = ref<boolean>(false);

const underlyingTokens = ref<UnderlyingToken[]>([]);

const assetIconFormRef: Ref<InstanceType<typeof AssetIconForm> | null> =
  ref(null);
const errors = ref<Record<string, string[]>>({});

const isEvmToken = computed<boolean>(() => get(assetType) === EVM_TOKEN);

const { allEvmChains } = useSupportedChains();

const { setMessage } = useMessageStore();

const { getAssetTypes, editAsset, addAsset } = useAssetManagementApi();

const { setValidation, setSubmitFunc, submitting } = useManagedAssetForm();

const externalServerValidation = () => true;

const v$ = setValidation(
  {
    assetType: { required },
    evmChain: { externalServerValidation },
    address: {
      required: requiredIf(isEvmToken),
      isValid: helpers.withMessage(
        t('asset_form.validation.valid_address'),
        (v: string) => !get(isEvmToken) || isValidEthAddress(v)
      )
    },
    tokenKind: { externalServerValidation },
    name: { externalServerValidation },
    symbol: { externalServerValidation },
    decimals: { externalServerValidation },
    coingecko: { externalServerValidation },
    cryptocompare: { externalServerValidation },
    started: { externalServerValidation },
    protocol: { externalServerValidation },
    swappedFor: { externalServerValidation },
    forked: { externalServerValidation }
  },
  {
    assetType,
    evmChain,
    tokenKind,
    address,
    name,
    symbol,
    decimals,
    coingecko,
    cryptocompare,
    started,
    protocol,
    swappedFor,
    forked
  },
  { $autoDirty: true, $externalResults: errors }
);

const clearFieldError = (field: keyof SupportedAsset) => {
  set(errors, omit(get(errors), field));
};

const clearFieldErrors = (fields: Array<keyof SupportedAsset>) => {
  fields.forEach(clearFieldError);
};

watch([address, evmChain], async ([address, evmChain]) => {
  if (!evmChain) {
    return;
  }

  if (get(dontAutoFetch) || !isValidEthAddress(address)) {
    set(dontAutoFetch, false);
    return;
  }

  set(fetching, true);
  const {
    decimals: newDecimals,
    name: newName,
    symbol: newSymbol
  } = await fetchTokenDetails({ address, evmChain });
  set(decimals, newDecimals ?? get(decimals));
  set(name, newName || get(name));
  set(symbol, newSymbol || get(symbol));
  set(fetching, false);
  clearFieldErrors(['decimals', 'name', 'symbol']);
});

watch(assetType, () => {
  // clearing errors because the errors are unique based on the asset type
  set(errors, {});
});

const parseDecimals = (value?: string): number | null => {
  if (!value) {
    return null;
  }

  const parsedValue = Number.parseInt(value);
  return Number.isNaN(parsedValue) ? null : parsedValue;
};

const asset: ComputedRef<Omit<SupportedAsset, 'identifier' | 'assetType'>> =
  computed(() => {
    const ut = get(underlyingTokens);

    return {
      address: get(address),
      name: get(name),
      symbol: get(symbol),
      decimals: parseDecimals(get(decimals)),
      coingecko: get(coingeckoEnabled) ? onlyIfTruthy(get(coingecko)) : null,
      cryptocompare: get(cryptocompareEnabled)
        ? onlyIfTruthy(get(cryptocompare))
        : '',
      started: time(get(started)),
      underlyingTokens: ut.length > 0 ? ut : undefined,
      swappedFor: onlyIfTruthy(get(swappedFor)),
      protocol: onlyIfTruthy(get(protocol)),
      evmChain: get(evmChain) || null,
      tokenKind: (get(tokenKind) as EvmTokenKind) || null
    };
  });

onBeforeMount(async () => {
  try {
    const queriedTypes = await getAssetTypes();
    set(
      types,
      queriedTypes.filter(item => item !== CUSTOM_ASSET)
    );
  } catch (e: any) {
    setMessage({
      description: t('asset_form.types.error', {
        message: e.message
      }).toString()
    });
  }
});

onMounted(() => {
  const token = get(editableItem);
  set(dontAutoFetch, !!token);
  if (!token) {
    return;
  }

  set(name, token.name ?? '');
  set(symbol, token.symbol);
  set(identifier, token.identifier ?? '');
  set(swappedFor, token.swappedFor ?? '');
  set(started, token.started ? convertFromTimestamp(token.started) : '');
  set(coingecko, token.coingecko ?? '');
  set(cryptocompare, token.cryptocompare ?? '');

  set(coingeckoEnabled, token.coingecko !== null);
  set(cryptocompareEnabled, token.cryptocompare !== '');

  set(forked, token.forked ?? '');
  set(assetType, token.assetType ?? EVM_TOKEN);
  set(address, token.address);
  set(decimals, token.decimals?.toString() ?? undefined);
  set(protocol, token.protocol ?? '');
  set(underlyingTokens, token.underlyingTokens ?? []);
  set(evmChain, token.evmChain);
  set(tokenKind, token.tokenKind);
});

const saveAsset = async () => {
  let newIdentifier: string;
  const assetVal = get(asset);

  const assetPayload = get(isEvmToken)
    ? assetVal
    : omit(assetVal, [
        'decimals',
        'address',
        'evmChain',
        'type',
        'tokenKind',
        'underlyingTokens'
      ]);

  const payload = {
    ...assetPayload,
    assetType: get(assetType)
  };

  if (get(editableItem)) {
    newIdentifier = get(identifier);
    await editAsset({ ...payload, identifier: newIdentifier });
  } else {
    ({ identifier: newIdentifier } = await addAsset(payload));
  }
  return newIdentifier;
};

const getUnderlyingTokenErrors = (
  underlyingTokens:
    | string
    | Record<string, { address: string[]; weight: string[] }>
) => {
  if (typeof underlyingTokens === 'string') {
    return [underlyingTokens];
  }

  const messages: string[] = [];
  for (const underlyingToken of Object.values(underlyingTokens)) {
    const ut = underlyingToken;
    if (ut.address) {
      messages.push(...ut.address);
    }
    if (underlyingTokens.weight) {
      messages.push(...ut.weight);
    }
  }
  return messages;
};

const handleError = (
  message:
    | {
        underlyingTokens:
          | string
          | Record<string, { address: string[]; weight: string[] }>;
      }
    | {
        _schema: string[];
      }
) => {
  if ('underlyingTokens' in message) {
    const messages = getUnderlyingTokenErrors(message.underlyingTokens);
    setMessage({
      title: t('asset_form.underlying_tokens').toString(),
      description: messages.join(',')
    });
  } else {
    setMessage({
      title: t('asset_form.underlying_tokens').toString(),
      description: message._schema[0]
    });
  }
};

const { deleteCacheKey } = useAssetCacheStore();

const save = async () => {
  try {
    const newIdentifier = await saveAsset();
    set(identifier, newIdentifier);
    await get(assetIconFormRef)?.saveIcon(newIdentifier);
    deleteCacheKey(newIdentifier);
    return true;
  } catch (e: any) {
    let errorsMessage = e.message;
    if (e instanceof ApiValidationError) {
      errorsMessage = e.getValidationErrors(get(asset));
    }

    if (typeof errorsMessage === 'string') {
      setMessage({
        title: get(editableItem)
          ? t('asset_form.edit_error')
          : t('asset_form.add_error'),
        description: errorsMessage
      });
    } else {
      if (errorsMessage.underlyingTokens || errorsMessage._schema) {
        handleError(errorsMessage);
      }
      set(errors, omit(errorsMessage, ['underlyingTokens', '_schema']));
      await get(v$).$validate();
    }

    return false;
  }
};

setSubmitFunc(save);

const { coingeckoContributeUrl, cryptocompareContributeUrl } = useInterop();
</script>

<template>
  <Fragment>
    <div
      v-if="editableItem"
      class="flex items-center text-caption text-rui-text-secondary -mt-2 mb-4 gap-2"
    >
      <span class="font-medium"> {{ t('asset_form.identifier') }}: </span>
      <div class="flex items-center">
        {{ editableItem.identifier }}
        <CopyButton
          class="ml-2"
          size="sm"
          :value="editableItem.identifier"
          :tooltip="t('asset_form.identifier_copy')"
        />
      </div>
    </div>
    <div class="flex flex-col gap-2">
      <div data-cy="type-select">
        <VSelect
          v-model="assetType"
          outlined
          :label="t('asset_form.labels.asset_type')"
          :disabled="types.length === 1 || !!editableItem"
          :items="types"
        >
          <template #item="{ item }">{{ toSentenceCase(item) }}</template>
          <template #selection="{ item }">
            {{ toSentenceCase(item) }}
          </template>
        </VSelect>
      </div>

      <div v-if="isEvmToken" class="grid md:grid-cols-2 gap-x-4 gap-y-2">
        <div data-cy="chain-select">
          <VSelect
            v-model="evmChain"
            outlined
            :label="t('asset_form.labels.chain')"
            :disabled="!!editableItem"
            :items="allEvmChains"
            item-value="name"
            item-text="label"
            :error-messages="toMessages(v$.evmChain)"
          />
        </div>

        <div data-cy="token-select">
          <VSelect
            v-model="tokenKind"
            outlined
            :label="t('asset_form.labels.token_kind')"
            :disabled="!!editableItem"
            :items="evmTokenKindsData"
            item-text="label"
            item-value="identifier"
            :error-messages="toMessages(v$.tokenKind)"
          />
        </div>
      </div>
      <div data-cy="address-input">
        <RuiTextField
          v-if="isEvmToken"
          v-model="address"
          variant="outlined"
          color="primary"
          :loading="fetching"
          :error-messages="toMessages(v$.address)"
          :label="t('common.address')"
          :disabled="submitting || fetching || !!editableItem"
          @keydown.space.prevent
        />
      </div>

      <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-2">
        <RuiTextField
          v-model="name"
          data-cy="name-input"
          class="md:col-span-2"
          variant="outlined"
          color="primary"
          :error-messages="toMessages(v$.name)"
          :label="t('common.name')"
          :disabled="submitting || fetching"
        />

        <RuiTextField
          v-model="symbol"
          :class="isEvmToken ? 'md:col-span-1' : 'md:col-span-2'"
          data-cy="symbol-input"
          variant="outlined"
          color="primary"
          :error-messages="toMessages(v$.symbol)"
          :label="t('asset_form.labels.symbol')"
          :disabled="submitting || fetching"
        />
        <div v-if="isEvmToken" data-cy="decimal-input">
          <RuiTextField
            v-model="decimals"
            variant="outlined"
            color="primary"
            min="0"
            max="18"
            type="number"
            :label="t('asset_form.labels.decimals')"
            :error-messages="toMessages(v$.decimals)"
            :disabled="submitting || fetching"
          />
        </div>
        <div class="md:col-span-2 flex items-start gap-4">
          <RuiTextField
            v-model="coingecko"
            variant="outlined"
            color="primary"
            clearable
            class="flex-1"
            :hint="t('asset_form.labels.coingecko_hint')"
            :label="t('asset_form.labels.coingecko')"
            :error-messages="toMessages(v$.coingecko)"
            :disabled="submitting || !coingeckoEnabled"
          >
            <template #append>
              <HelpLink
                small
                :url="coingeckoContributeUrl"
                :tooltip="t('asset_form.help_coingecko')"
              />
            </template>
          </RuiTextField>
          <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
            <template #activator>
              <RuiCheckbox
                v-model="coingeckoEnabled"
                class="mt-2"
                color="primary"
              />
            </template>
            <span> {{ t('asset_form.oracle_disable') }}</span>
          </RuiTooltip>
        </div>
        <div class="md:col-span-2 flex items-start gap-4">
          <RuiTextField
            v-model="cryptocompare"
            variant="outlined"
            color="primary"
            clearable
            class="flex-1"
            :label="t('asset_form.labels.cryptocompare')"
            :hint="t('asset_form.labels.cryptocompare_hint')"
            :error-messages="toMessages(v$.cryptocompare)"
            :disabled="submitting || !cryptocompareEnabled"
          >
            <template #append>
              <HelpLink
                small
                :url="cryptocompareContributeUrl"
                :tooltip="t('asset_form.help_cryptocompare')"
              />
            </template>
          </RuiTextField>
          <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
            <template #activator>
              <RuiCheckbox
                v-model="cryptocompareEnabled"
                class="mt-2"
                color="primary"
              />
            </template>
            <span> {{ t('asset_form.oracle_disable') }}</span>
          </RuiTooltip>
        </div>
      </div>

      <RuiCard no-padding rounded="sm" class="mt-2 mb-4 overflow-hidden">
        <VExpansionPanels flat tile>
          <VExpansionPanel>
            <VExpansionPanelHeader>
              {{ t('asset_form.optional') }}
            </VExpansionPanelHeader>
            <VExpansionPanelContent>
              <DateTimePicker
                v-model="started"
                outlined
                :label="t('asset_form.labels.started')"
                :error-messages="toMessages(v$.started)"
                :disabled="submitting"
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
                  :disabled="submitting"
                />
                <AssetSelect
                  v-model="swappedFor"
                  outlined
                  persistent-hint
                  clearable
                  :label="t('asset_form.labels.swapped_for')"
                  :error-messages="toMessages(v$.swappedFor)"
                  :disabled="submitting"
                />
                <AssetSelect
                  v-if="!isEvmToken && assetType"
                  v-model="forked"
                  outlined
                  persistent-hint
                  clearable
                  :label="t('asset_form.labels.forked')"
                  :error-messages="toMessages(v$.forked)"
                  :disabled="submitting"
                />
              </div>
              <UnderlyingTokenManager
                v-if="isEvmToken"
                v-model="underlyingTokens"
              />
            </VExpansionPanelContent>
          </VExpansionPanel>
        </VExpansionPanels>
      </RuiCard>

      <AssetIconForm
        ref="assetIconFormRef"
        :identifier="identifier"
        refreshable
      />
    </div>
  </Fragment>
</template>
