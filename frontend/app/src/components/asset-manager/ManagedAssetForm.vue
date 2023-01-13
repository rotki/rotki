<script setup lang="ts">
import { onlyIfTruthy } from '@rotki/common';
import {
  type EvmTokenKind,
  type SupportedAsset,
  type UnderlyingToken
} from '@rotki/common/lib/data';
import { omit } from 'lodash';
import { type ComputedRef, type PropType, type Ref } from 'vue';
import UnderlyingTokenManager from '@/components/asset-manager/UnderlyingTokenManager.vue';
import CopyButton from '@/components/helper/CopyButton.vue';
import Fragment from '@/components/helper/Fragment';
import HelpLink from '@/components/helper/HelpLink.vue';
import { CUSTOM_ASSET, EVM_TOKEN } from '@/services/assets/consts';
import { deserializeApiErrorMessage } from '@/services/converters';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useMessageStore } from '@/store/message';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import {
  isValidEthAddress,
  sanitizeAddress,
  toSentenceCase
} from '@/utils/text';
import AssetIconForm from '@/components/asset-manager/AssetIconForm.vue';
import { useAssetManagementApi } from '@/services/assets/management-api';
import { evmTokenKindsData } from '@/types/blockchain/chains';

function time(t: string): number | undefined {
  return t ? convertToTimestamp(t) : undefined;
}

const props = defineProps({
  value: { required: true, type: Boolean },
  edit: {
    required: false,
    type: Object as PropType<SupportedAsset | null>,
    default: null
  },
  saving: { required: false, type: Boolean, default: false }
});

const emit = defineEmits<{ (e: 'input', valid: boolean): void }>();

const { t, tc } = useI18n();
const { edit } = toRefs(props);
const { fetchTokenDetails } = useAssetInfoRetrieval();

const input = (value: boolean) => {
  emit('input', value);
};

const address = ref<string>('');
const name = ref<string>('');
const symbol = ref<string>('');
const decimals = ref<string>('');
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

const isEvmToken = computed<boolean>(() => {
  return get(assetType) === EVM_TOKEN;
});

const { evmChainNames } = useSupportedChains();

const { setMessage } = useMessageStore();

const {
  getAssetTypes,
  editEthereumToken,
  addEthereumToken,
  editAsset,
  addAsset
} = useAssetManagementApi();

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
  set(decimals, newDecimals?.toString() || get(decimals));
  set(name, newName || get(name));
  set(symbol, newSymbol || get(symbol));
  set(fetching, false);
});

const asset: ComputedRef<Omit<SupportedAsset, 'identifier' | 'type'>> =
  computed(() => {
    const ut = get(underlyingTokens);
    return {
      address: get(address),
      name: get(name),
      symbol: get(symbol),
      decimals: Number.parseInt(get(decimals)),
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
  set(assetType, token.type);
  set(address, token.address);
  set(decimals, token.decimals ? token.decimals.toString() : '');
  set(protocol, token.protocol ?? '');
  set(underlyingTokens, token.underlyingTokens ?? []);
  set(evmChain, token.evmChain);
  set(tokenKind, token.tokenKind);
});

const saveEthereumToken = async () => {
  let newIdentifier: string;
  const tokenVal = get(asset)!;
  if (get(edit) && get(identifier)) {
    ({ identifier: newIdentifier } = await editEthereumToken(tokenVal));
  } else {
    ({ identifier: newIdentifier } = await addEthereumToken(tokenVal));
  }
  return newIdentifier;
};

const saveAsset = async () => {
  let newIdentifier: string;
  const assetVal = get(asset);
  const payload = {
    ...omit(assetVal, ['decimals', 'address', 'evmChain', 'type', 'tokenKind']),
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

const getUnderlyingTokenErrors = (underlyingTokens: any) => {
  const messages: string[] = [];
  for (const underlyingToken of Object.values(underlyingTokens)) {
    const ut = underlyingToken as any;
    if (ut.address) {
      messages.push(...(ut.address as string[]));
    }
    if (underlyingTokens.weight) {
      messages.push(...(ut.weight as string[]));
    }
  }
  return messages;
};

const handleError = (message: any) => {
  if (message.token) {
    const token = message.token;
    set(errors, token);
    const underlyingTokens = token.underlying_tokens;
    if (underlyingTokens) {
      const messages = getUnderlyingTokenErrors(underlyingTokens);
      setMessage({
        title: t('asset_form.underlying_tokens').toString(),
        description: messages.join(',')
      });
    } else if (token._schema) {
      setMessage({
        title: t('asset_form.underlying_tokens').toString(),
        description: token._schema[0]
      });
    }
  } else {
    set(errors, message);
  }
};

const save = async () => {
  try {
    const newIdentifier = get(isEvmToken)
      ? await saveEthereumToken()
      : await saveAsset();
    set(identifier, newIdentifier);
    await get(assetIconFormRef)?.saveIcon(newIdentifier);
    return true;
  } catch (e: any) {
    const message = deserializeApiErrorMessage(e.message) as any;
    if (!message) {
      setMessage({
        title: tc('asset_form.underlying_tokens'),
        description: e.message
      });
    } else {
      handleError(message);
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
          :tooltip="tc('asset_form.identifier_copy')"
        />
      </v-col>
    </v-row>
    <v-form :value="value" class="pt-2" @input="input">
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
        <v-col md="6">
          <v-select
            v-model="evmChain"
            outlined
            :label="t('asset_form.labels.chain')"
            :disabled="!isEvmToken || !!edit"
            :items="evmChainNames"
            :error-messages="errors['evm_chain']"
            @focus="delete errors['evm_chain']"
          />
        </v-col>
        <v-col md="6">
          <v-select
            v-model="tokenKind"
            outlined
            :label="t('asset_form.labels.token_kind')"
            :disabled="!isEvmToken || !!edit"
            :items="evmTokenKindsData"
            item-text="label"
            item-value="identifier"
            :error-messages="errors['token_kind']"
            @focus="delete errors['token_kind']"
          />
        </v-col>
      </v-row>
      <v-row v-if="isEvmToken">
        <v-col>
          <v-text-field
            v-model="address"
            outlined
            :loading="fetching"
            :error-messages="errors['address']"
            :label="t('common.address')"
            :disabled="saving || fetching || !!edit"
            @keydown.space.prevent
            @focus="delete errors['address']"
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
            @focus="delete errors['name']"
          />
        </v-col>
        <v-col cols="12" :md="isEvmToken ? 3 : 6">
          <v-text-field
            v-model="symbol"
            outlined
            :error-messages="errors['symbol']"
            :label="t('asset_form.labels.symbol')"
            :disabled="saving || fetching"
            @focus="delete errors['symbol']"
          />
        </v-col>
        <v-col v-if="isEvmToken" cols="12" md="3">
          <v-text-field
            v-model="decimals"
            type="number"
            outlined
            min="0"
            max="18"
            :label="t('asset_form.labels.decimals')"
            :error-messages="errors['decimals']"
            :disabled="saving || fetching"
            @focus="delete errors['decimals']"
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
            @focus="delete errors['coingecko']"
          >
            <template #append>
              <help-link
                small
                :url="coingeckoContributeUrl"
                :tooltip="tc('asset_form.help_coingecko')"
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
            @focus="delete errors['cryptocompare']"
          >
            <template #append>
              <help-link
                small
                :url="cryptocompareContributeUrl"
                :tooltip="tc('asset_form.help_cryptocompare')"
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
              :label="tc('asset_form.labels.started')"
              :error-messages="errors['started']"
              :disabled="saving"
              @focus="delete errors['started']"
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
                  @focus="delete errors['protocol']"
                />
              </v-col>
              <v-col cols="12" md="6">
                <asset-select
                  v-model="swappedFor"
                  outlined
                  persistent-hint
                  clearable
                  :label="tc('asset_form.labels.swapped_for')"
                  :error-messages="errors['swapped_for']"
                  :disabled="saving"
                  @focus="delete errors['swapped_for']"
                />
              </v-col>
              <v-col v-if="!isEvmToken" cols="12" md="6">
                <asset-select
                  v-if="assetType"
                  v-model="forked"
                  outlined
                  persistent-hint
                  clearable
                  :label="tc('asset_form.labels.forked')"
                  :error-messages="errors['forked']"
                  :disabled="saving"
                  @focus="delete errors['forked']"
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
