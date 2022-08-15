import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import logger from 'loglevel';
import { acceptHMRUpdate, defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useMainStore } from '@/store/main';
import { ActionStatus } from '@/store/types';
import { READ_ONLY_TAGS, Tag, Tags } from '@/types/user';

export const useTagStore = defineStore('session/tags', () => {
  const allTags = ref<Tags>({});

  const tags = computed(() => {
    return Object.values(get(allTags));
  });

  const availableTags = computed(() => {
    return { ...get(allTags), ...READ_ONLY_TAGS };
  });

  const { setMessage } = useMainStore();

  const addTag = async (tag: Tag): Promise<ActionStatus> => {
    try {
      set(allTags, await api.addTag(tag));
      return { success: true };
    } catch (e: any) {
      setMessage({
        title: i18n.t('actions.session.tag_add.error.title').toString(),
        description: e.message
      });
      return {
        success: false,
        message: e.message
      };
    }
  };

  const editTag = async (tag: Tag) => {
    try {
      set(allTags, await api.editTag(tag));
    } catch (e: any) {
      setMessage({
        title: i18n.t('actions.session.tag_edit.error.title').toString(),
        description: e.message
      });
    }
  };

  const deleteTag = async (name: string) => {
    try {
      set(allTags, await api.deleteTag(name));
    } catch (e: any) {
      setMessage({
        title: i18n.t('actions.session.tag_delete.error.title').toString(),
        description: e.message
      });
    }
    const { removeBlockchainTags } = useBlockchainAccountsStore();
    await removeBlockchainTags(name);
  };

  const fetchTags = async () => {
    try {
      set(allTags, await api.getTags());
    } catch (e: any) {
      logger.error('Tags fetch failed', e);
    }
  };

  const reset = () => {
    set(allTags, {});
  };

  return {
    allTags,
    tags,
    availableTags,
    fetchTags,
    addTag,
    editTag,
    deleteTag,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTagStore, import.meta.hot));
}
