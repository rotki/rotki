\
<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { helpers, required } from '@vuelidate/validators';
import { isEmpty } from 'lodash-es';
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

const { setValidation } = useAccountDialog();

const v$ = setValidation(
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
  <div class="mt-2">
    <div class="flex gap-4">
      <VSelect
        v-model="xpubKeyPrefix"
        outlined
        class="account-form__xpub-key-type flex-1"
        item-value="value"
        item-text="label"
        :disabled="disabled"
        :items="keyTypeListData"
      />
      <RuiTextField
        v-model="xpubKey"
        variant="outlined"
        color="primary"
        class="account-form__xpub flex-1"
        :label="t('account_form.labels.btc.xpub')"
        autocomplete="off"
        :error-messages="toMessages(v$.xpub)"
        :disabled="disabled"
        @blur="v$.xpub.$touch()"
        @paste="onPasteXpub($event)"
      />
      <div>
        <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
          <template #activator>
            <div class="account-form__advanced">
              <RuiButton
                variant="text"
                icon
                class="mt-1"
                @click="advanced = !advanced"
              >
                <RuiIcon v-if="advanced" name="arrow-up-s-line" />
                <RuiIcon v-else name="arrow-down-s-line" />
              </RuiButton>
            </div>
          </template>
          <span>
            {{ t('account_form.advanced_tooltip', advanced ? 0 : 1) }}
          </span>
        </RuiTooltip>
      </div>
    </div>
    <RuiTextField
      v-if="advanced"
      v-model="derivationPath"
      variant="outlined"
      color="primary"
      class="account-form__derivation-path"
      :label="t('account_form.labels.btc.derivation_path')"
      :error-messages="toMessages(v$.derivationPath)"
      autocomplete="off"
      :disabled="disabled"
      persistent-hint
      :hint="t('account_form.labels.btc.derivation_path_hint')"
      @blur="v$.derivationPath.$touch()"
    />
  </div>
</template>
