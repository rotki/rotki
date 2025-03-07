<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { XpubPayload } from '@/types/blockchain/accounts';
import type { BtcChains } from '@/types/blockchain/chains';
import { trimOnPaste } from '@/utils/event';
import { toMessages } from '@/utils/validation';
import { getKeyType, getPrefix, isPrefixed, keyType, XpubPrefix, type XpubType } from '@/utils/xpub';
import { Blockchain } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required } from '@vuelidate/validators';
import { isEmpty } from 'es-toolkit/compat';

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });

const props = defineProps<{
  disabled: boolean;
  xpub: XpubPayload | undefined;
  blockchain: BtcChains;
}>();

const emit = defineEmits<{
  (e: 'update:xpub', xpub: XpubPayload | undefined): void;
}>();

const { t } = useI18n();

const { blockchain, disabled, xpub } = toRefs(props);

const xpubKey = ref<string>('');
const derivationPath = ref<string>('');
const xpubKeyPrefix = ref<XpubPrefix>(XpubPrefix.XPUB);
const advanced = ref(false);

function updateXpub(event?: XpubPayload) {
  emit('update:xpub', event);
}

function setXpubKeyType(value: string) {
  const match = isPrefixed(value);
  if (match && match.length === 3) {
    const prefix = match[1] as XpubPrefix;
    if (prefix === XpubPrefix.XPUB)
      return;

    set(xpubKeyPrefix, prefix);
  }
}

function onPasteXpub(event: ClipboardEvent) {
  if (get(disabled))
    return;

  const paste = trimOnPaste(event);
  if (paste) {
    setXpubKeyType(paste);
    set(xpubKey, paste);
  }
}

const keyTypeListData = computed<XpubType[]>(() => {
  if (get(blockchain) === Blockchain.BTC)
    return keyType;

  return keyType.filter(item => ![XpubPrefix.ZPUB, XpubPrefix.P2TR].includes(item.value));
});

const rules = {
  derivationPath: {
    basic: () => true,
  },
  xpub: {
    required: helpers.withMessage(t('account_form.validation.xpub_non_empty'), required),
  },
};

const v$ = useVuelidate(
  rules,
  {
    derivationPath,
    xpub,
  },
  {
    $autoDirty: true,
    $externalResults: errors,
    $stopPropagation: true,
  },
);

function validate(): Promise<boolean> {
  return get(v$).$validate();
}

watch(errors, (errors) => {
  if (!isEmpty(errors))
    get(v$).$validate();
});

watchImmediate(xpub, (xpub) => {
  set(xpubKey, xpub?.xpub || '');
  const prefix = getPrefix(xpub?.xpubType);
  if (prefix !== XpubPrefix.XPUB)
    set(xpubKeyPrefix, prefix);

  const derivation = get(derivationPath);
  if (derivation && derivation.replace(/'/g, '').replace(/\/$/, '') !== xpub?.derivationPath)
    set(derivationPath, xpub?.derivationPath || '');
});

watch(blockchain, () => {
  set(xpubKeyPrefix, get(keyTypeListData)[0].value);
});

watch([xpubKeyPrefix, xpubKey, derivationPath], ([prefix, xpub, path]) => {
  if (xpub)
    setXpubKeyType(xpub);

  let payload: XpubPayload | undefined;
  if (xpub) {
    payload = {
      derivationPath: path?.replace(/'/g, '').replace(/\/$/, '') ?? undefined,
      xpub: xpub.trim(),
      xpubType: getKeyType(prefix as XpubPrefix),
    };
  }
  updateXpub(payload);
});

defineExpose({
  validate,
});
</script>

<template>
  <div class="mt-2 flex flex-col gap-4">
    <div class="flex gap-4">
      <RuiMenuSelect
        v-model="xpubKeyPrefix"
        :options="keyTypeListData"
        :disabled="disabled"
        class="account-form__xpub-key-type flex-1"
        key-attr="value"
        text-attr="label"
        hide-details
        variant="outlined"
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
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <div class="account-form__advanced">
              <RuiButton
                variant="text"
                icon
                class="mt-1"
                @click="advanced = !advanced"
              >
                <RuiIcon
                  v-if="advanced"
                  name="lu-chevron-up"
                />
                <RuiIcon
                  v-else
                  name="lu-chevron-down"
                />
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
      :hint="t('common.optional')"
      @blur="v$.derivationPath.$touch()"
    />
  </div>
</template>
