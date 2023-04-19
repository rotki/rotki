<script setup lang="ts">
import { type BtcChains } from '@/types/blockchain/chains';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import {
  type XpubAccountWithBalance,
  type XpubPayload
} from '@/types/blockchain/accounts';

const props = defineProps<{ blockchain: BtcChains }>();

const { blockchain } = toRefs(props);

const xpub = ref<XpubPayload | null>(null);
const label = ref('');
const tags = ref<string[]>([]);

const errorMessages = ref<ValidationErrors>({});

const { addAccounts, fetchAccounts } = useBlockchains();
const { editAccount } = useBlockchainAccounts();
const { setMessage } = useMessageStore();
const { valid, setSave, accountToEdit } = useAccountDialog();
const { pending, loading } = useAccountLoading();
const { tc } = useI18n();

const save = async () => {
  const edit = !!get(accountToEdit);

  const chain = get(blockchain);
  try {
    set(pending, true);
    if (edit) {
      await editAccount({
        blockchain: chain,
        address: '',
        label: get(label),
        tags: get(tags),
        xpub: get(xpub) || undefined
      });
      startPromise(fetchAccounts(chain));
    } else {
      await addAccounts({
        blockchain: chain,
        payload: [
          {
            address: '',
            label: get(label),
            tags: get(tags),
            xpub: get(xpub) || undefined
          }
        ]
      });
    }

    set(xpub, null);
    set(label, '');
    set(tags, []);
  } catch (e: any) {
    logger.error(e);
    let errors = e.message;
    if (e instanceof ApiValidationError) {
      errors = e.getValidationErrors({
        xpub: '',
        derivationPath: ''
      });
    }

    if (typeof errors === 'string') {
      await setMessage({
        description: tc('account_form.error.description', 0, {
          error: errors
        }),
        title: tc('account_form.error.title'),
        success: false
      });
    } else {
      set(errorMessages, errors);
      return false;
    }

    return false;
  } finally {
    set(pending, false);
  }
  return true;
};

const setXpub = (acc: XpubAccountWithBalance): void => {
  set(xpub, {
    xpub: acc.xpub,
    derivationPath: acc.derivationPath,
    blockchain: get(blockchain),
    xpubType: ''
  });
  set(label, acc.label);
  set(tags, acc.tags);
};

watch(accountToEdit, acc => {
  if (acc) {
    assert('derivationPath' in acc);
    setXpub(acc);
  } else {
    set(xpub, null);
  }
});

onMounted(() => {
  setSave(save);

  const acc = get(accountToEdit);
  if (acc) {
    assert('derivationPath' in acc);
    setXpub(acc);
  }
});
</script>

<template>
  <v-form v-model="valid">
    <xpub-input
      :disabled="loading"
      :error-messages="errorMessages"
      :xpub="xpub"
      :blockchain="blockchain"
      @update:xpub="xpub = $event"
    />
    <account-data-input
      :tags="tags"
      :label="label"
      :disabled="loading"
      @update:label="label = $event"
      @update:tags="tags = $event"
    />
  </v-form>
</template>
