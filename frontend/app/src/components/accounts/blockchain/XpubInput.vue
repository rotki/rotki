\
<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import isEmpty from 'lodash/isEmpty';
import { XpubPrefix, type XpubType } from '@/utils/xpub';
import { type ValidationErrors } from '@/types/api/errors';
import { type BtcChains } from '@/types/blockchain/chains';
import { type XpubPayload } from '@/types/blockchain/accounts';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  disabled: boolean;
  errorMessages: ValidationErrors;
  xpub: XpubPayload | null;
  blockchain: BtcChains;
}>();

const emit = defineEmits<{
  (e: 'update:xpub', event: XpubPayload | null): void;
}>();

const { t } = useI18n();

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
  if (get(disabled)) {
    return;
  }
  const paste = trimOnPaste(event);
  if (paste) {
    setXpubKeyType(paste);
    set(xpubKey, paste);
  }
};

const keyTypeListData = computed<XpubType[]>(() => {
  if (get(blockchain) === Blockchain.BTC) {
    return keyType;
  }
  return keyType.filter(
    item => ![XpubPrefix.ZPUB, XpubPrefix.P2TR].includes(item.value)
  );
});

const rules = {
  xpub: {
    required: helpers.withMessage(
      t('account_form.validation.xpub_non_empty'),
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

watch(errorMessages, errors => {
  if (!isEmpty(errors)) {
    get(v$).$validate();
  }
});
</script>

<template>
  <div>
    <VRow align="center" no-gutters class="mt-2">
      <VCol cols="auto">
        <VSelect
          v-model="xpubKeyPrefix"
          outlined
          class="account-form__xpub-key-type"
          item-value="value"
          item-text="label"
          :disabled="disabled"
          :items="keyTypeListData"
        />
      </VCol>
      <VCol>
        <VTextField
          v-model="xpubKey"
          outlined
          class="account-form__xpub ml-2"
          :label="t('account_form.labels.btc.xpub')"
          autocomplete="off"
          :error-messages="toMessages(v$.xpub)"
          :disabled="disabled"
          @blur="v$.xpub.$touch()"
          @paste="onPasteXpub($event)"
        >
          <template #append-outer>
            <VTooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <div class="account-form__advanced">
                  <VBtn
                    icon
                    class="mt-n2"
                    v-bind="attrs"
                    v-on="on"
                    @click="advanced = !advanced"
                  >
                    <VIcon v-if="advanced">mdi-chevron-up</VIcon>
                    <VIcon v-else>mdi-chevron-down</VIcon>
                  </VBtn>
                </div>
              </template>
              <span>
                {{ t('account_form.advanced_tooltip', advanced ? 0 : 1) }}
              </span>
            </VTooltip>
          </template>
        </VTextField>
      </VCol>
    </VRow>
    <VRow v-if="advanced" no-gutters>
      <VCol>
        <VTextField
          v-model="derivationPath"
          outlined
          class="account-form__derivation-path"
          :label="t('account_form.labels.btc.derivation_path')"
          :error-messages="toMessages(v$.derivationPath)"
          autocomplete="off"
          :disabled="disabled"
          persistent-hint
          :hint="t('account_form.labels.btc.derivation_path_hint')"
          @blur="v$.derivationPath.$touch()"
        />
      </VCol>
    </VRow>
  </div>
</template>
