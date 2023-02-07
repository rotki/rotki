\
<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { trimOnPaste } from '@/utils/event';
import {
  XpubPrefix,
  type XpubType,
  getKeyType,
  getPrefix,
  keyType
} from '@/utils/xpub';
import { type ValidationErrors } from '@/types/api/errors';
import { type BtcChains } from '@/types/blockchain/chains';
import { type XpubPayload } from '@/types/blockchain/accounts';

const props = defineProps<{
  disabled: boolean;
  errorMessages: ValidationErrors;
  xpub: XpubPayload | null;
  blockchain: BtcChains;
}>();

const emit = defineEmits(['update:xpub']);

const { t, tc } = useI18n();

const { xpub, disabled, blockchain, errorMessages } = toRefs(props);

const xpubKey = ref('');
const derivationPath = ref('');
const xpubKeyPrefix = ref<XpubPrefix>(XpubPrefix.XPUB);
const advanced = ref(false);

const updateXpub = (event: XpubPayload | null) => {
  emit('update:xpub', event);
};

const isPrefixed = (value: string) => value.match(/([x-z]pub)(.*)/);
const setXpubKeyType = (value: string) => {
  const match = isPrefixed(value);
  if (match && match.length === 3) {
    const prefix = match[1] as XpubPrefix;
    if (prefix === XpubPrefix.XPUB) {
      return;
    }
    set(xpubKeyPrefix, prefix);
  }
};

watch(xpub, xpub => {
  set(xpubKey, xpub?.xpub);
  const prefix = getPrefix(xpub?.xpubType);
  if (prefix !== XpubPrefix.XPUB) {
    set(xpubKeyPrefix, prefix);
  }
  set(derivationPath, xpub?.derivationPath);
});

watch(blockchain, () => {
  set(xpubKeyPrefix, get(keyTypeListData)[0].value);
});

onMounted(() => {
  const payload = get(xpub);
  set(xpubKey, payload?.xpub || '');
  const prefix = getPrefix(payload?.xpubType);
  if (prefix !== XpubPrefix.XPUB) {
    set(xpubKeyPrefix, prefix);
  }
  set(derivationPath, payload?.derivationPath);
});

watch([xpubKeyPrefix, xpubKey, derivationPath], ([prefix, xpub, path]) => {
  if (xpub) {
    setXpubKeyType(xpub);
  }

  let payload: XpubPayload | null = null;
  if (xpub) {
    payload = {
      xpub: xpub.trim(),
      derivationPath: path ?? undefined,
      xpubType: getKeyType(prefix as XpubPrefix),
      blockchain: get(blockchain)
    };
  }
  updateXpub(payload);
});

const onPasteXpub = (event: ClipboardEvent) => {
  if (get(disabled)) return;
  const paste = trimOnPaste(event);
  if (paste) {
    setXpubKeyType(paste);
    set(xpubKey, paste);
  }
};

const keyTypeListData = computed<XpubType[]>(() => {
  if (get(blockchain) === Blockchain.BTC) return keyType;
  return keyType.filter(
    item => ![XpubPrefix.ZPUB, XpubPrefix.P2TR].includes(item.value)
  );
});

const rules = {
  xpub: {
    required: helpers.withMessage(
      tc('account_form.validation.xpub_non_empty'),
      required
    )
  },
  derivationPath: {
    basic: () => true
  }
};

const v$ = useVuelidate(
  rules,
  {
    xpub,
    derivationPath
  },
  {
    $autoDirty: true,
    $stopPropagation: true,
    $externalResults: errorMessages
  }
);
</script>

<template>
  <div>
    <v-row align="center" no-gutters class="mt-2">
      <v-col cols="auto">
        <v-select
          v-model="xpubKeyPrefix"
          outlined
          class="account-form__xpub-key-type"
          item-value="value"
          item-text="label"
          :disabled="disabled"
          :items="keyTypeListData"
        />
      </v-col>
      <v-col>
        <v-text-field
          v-model="xpubKey"
          outlined
          class="account-form__xpub ml-2"
          :label="t('account_form.labels.btc.xpub')"
          autocomplete="off"
          :error-messages="v$.xpub.$errors.map(e => e.$message)"
          :disabled="disabled"
          @blur="v$.xpub.$touch()"
          @paste="onPasteXpub"
        >
          <template #append-outer>
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <div class="account-form__advanced">
                  <v-btn
                    icon
                    class="mt-n2"
                    v-bind="attrs"
                    v-on="on"
                    @click="advanced = !advanced"
                  >
                    <v-icon v-if="advanced">mdi-chevron-up</v-icon>
                    <v-icon v-else>mdi-chevron-down</v-icon>
                  </v-btn>
                </div>
              </template>
              <span>
                {{ tc('account_form.advanced_tooltip', advanced ? 0 : 1) }}
              </span>
            </v-tooltip>
          </template>
        </v-text-field>
      </v-col>
    </v-row>
    <v-row v-if="advanced" no-gutters>
      <v-col>
        <v-text-field
          v-model="derivationPath"
          outlined
          class="account-form__derivation-path"
          :label="t('account_form.labels.btc.derivation_path')"
          :error-messages="v$.derivationPath.$errors.map(e => e.$message)"
          autocomplete="off"
          :disabled="disabled"
          persistent-hint
          :hint="t('account_form.labels.btc.derivation_path_hint')"
          @blur="v$.derivationPath.$touch()"
        />
      </v-col>
    </v-row>
  </div>
</template>
