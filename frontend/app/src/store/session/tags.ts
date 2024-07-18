import { READ_ONLY_TAGS, type Tag, type Tags } from '@/types/tags';
import type { ActionStatus } from '@/types/action';

export const useTagStore = defineStore('session/tags', () => {
  const allTags = ref<Tags>({});

  const tags = computed(() => Object.values(get(allTags)));

  const availableTags = computed<Record<string, Tag>>(() => ({
    ...get(allTags),
    ...READ_ONLY_TAGS,
  }));

  const { removeTag } = useBlockchainAccounts();
  const { setMessage } = useMessageStore();
  const { t } = useI18n();
  const { queryAddTag, queryTags, queryEditTag, queryDeleteTag } = useTagsApi();

  const addTag = async (tag: Tag): Promise<ActionStatus> => {
    try {
      set(allTags, await queryAddTag(tag));
      return { success: true };
    }
    catch (error: any) {
      setMessage({
        title: t('actions.session.tag_add.error.title'),
        description: error.message,
      });
      return {
        success: false,
        message: error.message,
      };
    }
  };

  const editTag = async (tag: Tag): Promise<ActionStatus> => {
    try {
      set(allTags, await queryEditTag(tag));
      return { success: true };
    }
    catch (error: any) {
      setMessage({
        title: t('actions.session.tag_edit.error.title'),
        description: error.message,
      });
      return {
        success: false,
        message: error.message,
      };
    }
  };

  const deleteTag = async (name: string): Promise<void> => {
    try {
      set(allTags, await queryDeleteTag(name));
      removeTag(name);
    }
    catch (error: any) {
      setMessage({
        title: t('actions.session.tag_delete.error.title'),
        description: error.message,
      });
    }
  };

  const fetchTags = async (): Promise<void> => {
    try {
      set(allTags, await queryTags());
    }
    catch (error: any) {
      logger.error('Tags fetch failed', error);
    }
  };

  return {
    allTags,
    tags,
    availableTags,
    fetchTags,
    addTag,
    editTag,
    deleteTag,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTagStore, import.meta.hot));
