import logger from 'loglevel';
import { ComputedRef } from 'vue';
import { useTagsApi } from '@/services/tags';
import { useBlockchainAccountsStore } from '@/store/blockchain/accounts';
import { useMessageStore } from '@/store/message';
import { ActionStatus } from '@/store/types';
import { READ_ONLY_TAGS, Tag, Tags } from '@/types/user';

export const useTagStore = defineStore('session/tags', () => {
  const allTags = ref<Tags>({});

  const tags = computed(() => {
    return Object.values(get(allTags));
  });

  const availableTags: ComputedRef<Record<string, Tag>> = computed(() => {
    return { ...get(allTags), ...READ_ONLY_TAGS };
  });

  const { removeTag } = useBlockchainAccountsStore();
  const { setMessage } = useMessageStore();
  const { tc } = useI18n();
  const { queryAddTag, queryTags, queryEditTag, queryDeleteTag } = useTagsApi();

  const addTag = async (tag: Tag): Promise<ActionStatus> => {
    try {
      set(allTags, await queryAddTag(tag));
      return { success: true };
    } catch (e: any) {
      setMessage({
        title: tc('actions.session.tag_add.error.title'),
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
      set(allTags, await queryEditTag(tag));
    } catch (e: any) {
      setMessage({
        title: tc('actions.session.tag_edit.error.title'),
        description: e.message
      });
    }
  };

  const deleteTag = async (name: string) => {
    try {
      set(allTags, await queryDeleteTag(name));
      removeTag(name);
    } catch (e: any) {
      setMessage({
        title: tc('actions.session.tag_delete.error.title'),
        description: e.message
      });
    }
  };

  const fetchTags = async () => {
    try {
      set(allTags, await queryTags());
    } catch (e: any) {
      logger.error('Tags fetch failed', e);
    }
  };

  return {
    allTags,
    tags,
    availableTags,
    fetchTags,
    addTag,
    editTag,
    deleteTag
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTagStore, import.meta.hot));
}
