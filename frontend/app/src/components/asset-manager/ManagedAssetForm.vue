<script setup lang="ts">
import { onlyIfTruthy } from '@rotki/common';
import {
  type EvmTokenKind,
  type SupportedAsset,
  type UnderlyingToken
} from '@rotki/common/lib/data';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import omit from 'lodash/omit';
import { type ComputedRef, type Ref } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { toSentenceCase } from '@/utils/text';
import { evmTokenKindsData } from '@/types/blockchain/chains';
import { CUSTOM_ASSET, EVM_TOKEN } from '@/types/asset';
import { ApiValidationError } from '@/types/api/errors';
import AssetIconForm from '@/components/asset-manager/AssetIconForm.vue';

function time(t: string): number | undefined {
  return t ? convertToTimestamp(t) : undefined;
}

const props = withDefaults(
  defineProps<{
    edit?: SupportedAsset | null;
    saving?: boolean;
  }>(),
  {
    edit: null
  }
);

const emit = defineEmits<{ (e: 'input', valid: boolean): void }>();

const { t } = useI18n();
const { edit } = toRefs(props);
const { fetchTokenDetails } = useAssetInfoRetrieval();

const input = (value: boolean) => {
  emit('input', value);
};

const address = ref<string>('');
const name = ref<string>('');
const symbol = ref<string>('');
const decimals = ref<number | null>(null);
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

const v$ = useVuelidate(
  {
    assetType: { required }
  },
  {
    assetType
  },
  { $autoDirty: true }
);

const clearFieldError = (field: keyof SupportedAsset) => {
  delete get(errors)[field];
};

const clearFieldErrors = (fields: Array<keyof SupportedAsset>) => {
  fields.forEach(clearFieldError);
};

watch(address, async () => {
  const sanitizedAddress = sanitizeAddress(get(address));
  if (get(address) !== sanitizedAddress) {
    set(address, sanitizedAddress);
    return;
  }

  if (get(dontAutoFetch) || !isValidEthAddress(get(address))) {
    set(dontAutoFetch, false);
    return;
  }

  set(fetching, true);
  const {
    decimals: newDecimals,
    name: newName,
    symbol: newSymbol
  } = await fetchTokenDetails(get(address));
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

const asset: ComputedRef<Omit<SupportedAsset, 'identifier' | 'assetType'>> =
  computed(() => {
    const ut = get(underlyingTokens);
    return {
      address: get(address),
      name: get(name),
      symbol: get(symbol),
      decimals: get(decimals),
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
  const token = get(edit);
  set(dontAutoFetch, !!get(edit));
  if (!token) {
    return;
  }

  set(name, token.name ?? '');
  set(symbol, token.symbol);
  set(identifier, token.identifier ?? '');
  set(swappedFor, token.swappedFor ?? '');
  set(started, token.started ? convertFromTimestamp(token.started, true) : '');
  set(coingecko, token.coingecko ?? '');
  set(cryptocompare, token.cryptocompare ?? '');

  set(coingeckoEnabled, token.coingecko !== null);
  set(cryptocompareEnabled, token.cryptocompare !== '');

  set(forked, token.forked ?? '');
  set(assetType, token.assetType);
  set(address, token.address);
  set(decimals, token.decimals ?? null);
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

  if (get(edit)) {
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

const save = async () => {
  try {
    const newIdentifier = await saveAsset();
    set(identifier, newIdentifier);
    await get(assetIconFormRef)?.saveIcon(newIdentifier);
    return true;
  } catch (e: any) {
    let errorsMessage = e.message;
    if (e instanceof ApiValidationError) {
      errorsMessage = e.getValidationErrors(get(asset));
    }

    if (typeof errorsMessage === 'string') {
      setMessage({
        title: get(edit)
          ? t('asset_form.edit_error')
          : t('asset_form.add_error'),
        description: errorsMessage
      });
    } else {
      if (errorsMessage.underlyingTokens || errorsMessage._schema) {
        handleError(errorsMessage);
      }
      set(errors, omit(errorsMessage, ['underlyingTokens', '_schema']));
    }

    return false;
  }
};

defineExpose({
  save
});

const { coingeckoContributeUrl, cryptocompareContributeUrl } = useInterop();
</script>

<template>
  <fragment>
    <v-row
      v-if="!!edit"
      class="text-caption text--secondary py-2"
      align="center"
    >
      <v-col cols="auto" class="font-weight-medium">
        {{ t('asset_form.identifier') }}
      </v-col>
      <v-col>
        {{ edit.identifier }}
        <copy-button
          :value="edit.identifier"
          :tooltip="t('asset_form.identifier_copy')"
        />
      </v-col>
    </v-row>
    <v-form :value="!v$.$invalid" class="pt-2" @input="input($event)">
      <v-row>
        <v-col cols="12">
          <v-select
            v-model="assetType"
            outlined
            :label="t('asset_form.labels.asset_type')"
            :disabled="types.length === 1 || !!edit"
            :items="types"
          >
            <template #item="{ item }">{{ toSentenceCase(item) }}</template>
            <template #selection="{ item }">
              {{ toSentenceCase(item) }}
            </template>
          </v-select>
        </v-col>
        <v-col md="6" data-cy="chain-select">
          <v-select
            v-model="evmChain"
            outlined
            :label="t('asset_form.labels.chain')"
            :disabled="!isEvmToken || !!edit"
            :items="allEvmChains"
            item-value="name"
            item-text="name"
            :error-messages="errors['evmChain']"
            @focus="clearFieldError('evmChain')"
          />
        </v-col>
        <v-col md="6" data-cy="token-select">
          <v-select
            v-model="tokenKind"
            outlined
            :label="t('asset_form.labels.token_kind')"
            :disabled="!isEvmToken || !!edit"
            :items="evmTokenKindsData"
            item-text="label"
            item-value="identifier"
            :error-messages="errors['tokenKind']"
            @focus="clearFieldError('tokenKind')"
          />
        </v-col>
      </v-row>
      <v-row v-if="isEvmToken">
        <v-col data-cy="address-input">
          <v-text-field
            v-model="address"
            outlined
            :loading="fetching"
            :error-messages="errors['address']"
            :label="t('common.address')"
            :disabled="saving || fetching || !!edit"
            @keydown.space.prevent
            @focus="clearFieldError('address')"
          />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="name"
            outlined
            :error-messages="errors['name']"
            :label="t('common.name')"
            :disabled="saving || fetching"
            @focus="clearFieldError('name')"
          />
        </v-col>
        <v-col cols="12" :md="isEvmToken ? 3 : 6" data-cy="symbol-input">
          <v-text-field
            v-model="symbol"
            outlined
            :error-messages="errors['symbol']"
            :label="t('asset_form.labels.symbol')"
            :disabled="saving || fetching"
            @focus="clearFieldError('symbol')"
          />
        </v-col>
        <v-col v-if="isEvmToken" cols="12" md="3" data-cy="decimal-input">
          <v-text-field
            v-model.number="decimals"
            type="number"
            outlined
            min="0"
            max="18"
            :label="t('asset_form.labels.decimals')"
            :error-messages="errors['decimals']"
            :disabled="saving || fetching"
            @focus="clearFieldError('decimals')"
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6" class="d-flex flex-row">
          <v-text-field
            v-model="coingecko"
            outlined
            clearable
            persistent-hint
            :hint="t('asset_form.labels.coingecko_hint')"
            :label="t('asset_form.labels.coingecko')"
            :error-messages="errors['coingecko']"
            :disabled="saving || !coingeckoEnabled"
            @focus="clearFieldError('coingecko')"
          >
            <template #append>
              <help-link
                small
                :url="coingeckoContributeUrl"
                :tooltip="t('asset_form.help_coingecko')"
              />
            </template>
          </v-text-field>
          <v-tooltip open-delay="400" top max-width="320">
            <template #activator="{ attrs, on }">
              <span v-bind="attrs" v-on="on">
                <v-checkbox v-model="coingeckoEnabled" class="ms-4 me-2" />
              </span>
            </template>
            <span> {{ t('asset_form.oracle_disable') }}</span>
          </v-tooltip>
        </v-col>
        <v-col cols="12" md="6" class="d-flex flex-row">
          <v-text-field
            v-model="cryptocompare"
            outlined
            persistent-hint
            clearable
            :label="t('asset_form.labels.cryptocompare')"
            :hint="t('asset_form.labels.cryptocompare_hint')"
            :error-messages="errors['cryptocompare']"
            :disabled="saving || !cryptocompareEnabled"
            @focus="clearFieldError('cryptocompare')"
          >
            <template #append>
              <help-link
                small
                :url="cryptocompareContributeUrl"
                :tooltip="t('asset_form.help_cryptocompare')"
              />
            </template>
          </v-text-field>
          <v-tooltip open-delay="400" top max-width="320">
            <template #activator="{ attrs, on }">
              <span v-bind="attrs" v-on="on">
                <v-checkbox v-model="cryptocompareEnabled" class="ms-4 me-2" />
              </span>
            </template>
            <span> {{ t('asset_form.oracle_disable') }}</span>
          </v-tooltip>
        </v-col>
      </v-row>
    </v-form>

    <v-sheet outlined rounded class="mt-2">
      <v-expansion-panels flat tile>
        <v-expansion-panel>
          <v-expansion-panel-header>
            {{ t('asset_form.optional') }}
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <date-time-picker
              v-model="started"
              seconds
              outlined
              :label="t('asset_form.labels.started')"
              :error-messages="errors['started']"
              :disabled="saving"
              @focus="clearFieldError('started')"
            />
            <v-row>
              <v-col v-if="isEvmToken" cols="12" md="6">
                <v-text-field
                  v-model="protocol"
                  outlined
                  persistent-hint
                  clearable
                  clear-icon="mdi-close"
                  class="asset-form__protocol"
                  :label="t('common.protocol')"
                  :error-messages="errors['protocol']"
                  :disabled="saving"
                  @focus="clearFieldError('protocol')"
                />
              </v-col>
              <v-col cols="12" md="6">
                <asset-select
                  v-model="swappedFor"
                  outlined
                  persistent-hint
                  clearable
                  :label="t('asset_form.labels.swapped_for')"
                  :error-messages="errors['swappedFor']"
                  :disabled="saving"
                  @focus="clearFieldError('swappedFor')"
                />
              </v-col>
              <v-col v-if="!isEvmToken" cols="12" md="6">
                <asset-select
                  v-if="assetType"
                  v-model="forked"
                  outlined
                  persistent-hint
                  clearable
                  :label="t('asset_form.labels.forked')"
                  :error-messages="errors['forked']"
                  :disabled="saving"
                  @focus="clearFieldError('forked')"
                />
              </v-col>
            </v-row>
            <underlying-token-manager
              v-if="isEvmToken"
              v-model="underlyingTokens"
            />
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-sheet>

    <div class="my-4">
      <asset-icon-form
        ref="assetIconFormRef"
        :identifier="identifier"
        refreshable
      />
    </div>
  </fragment>
</template>
