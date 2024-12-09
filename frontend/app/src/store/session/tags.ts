import { logger } from '@/utils/logging';
import { useMessageStore } from '@/store/message';
import { useTagsApi } from '@/composables/api/tags';
import { useBlockchainAccounts } from '@/composables/blockchain/accounts';
import type { Tag, Tags } from '@/types/tags';
import type { ActionStatus } from '@/types/action';

export const useTagStore = defineStore('session/tags', () => {
  const allTags = ref<Tags>({});

  const tags = computed(() => Object.values(get(allTags)));

  const { removeTag } = useBlockchainAccounts();
  const { setMessage } = useMessageStore();
  const { t } = useI18n();
  const { queryAddTag, queryDeleteTag, queryEditTag, queryTags } = useTagsApi();

  const addTag = async (tag: Tag): Promise<ActionStatus> => {
    try {
      set(allTags, await queryAddTag(tag));
      return { success: true };
    }
    catch (error: any) {
      setMessage({
        description: error.message,
        title: t('actions.session.tag_add.error.title'),
      });
      return {
        message: error.message,
        success: false,
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
        description: error.message,
        title: t('actions.session.tag_edit.error.title'),
      });
      return {
        message: error.message,
        success: false,
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
        description: error.message,
        title: t('actions.session.tag_delete.error.title'),
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

  function tagExists(tagName: string): boolean {
    return get(tags)
      .map(({ name }) => name)
      .includes(tagName);
  }

  async function attemptTagCreation(tag: string, backgroundColor?: string): Promise<boolean> {
    if (tagExists(tag))
      return true;

    const bgColor = backgroundColor || randomColor();
    const fgColor = invertColor(bgColor);

    const newTag: Tag = {
      backgroundColor: bgColor,
      description: '',
      foregroundColor: fgColor,
      name: tag,
    };

    try {
      const { success } = await addTag(newTag);
      return success;
    }
    catch (error) {
      logger.error(error);
      return false;
    }
  };

  return {
    addTag,
    allTags,
    attemptTagCreation,
    deleteTag,
    editTag,
    fetchTags,
    tags,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTagStore, import.meta.hot));
