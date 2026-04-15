import type { ActionStatus } from '@/modules/common/action';
import type { Tag } from '@/modules/tags/tags';
import { invertColor, randomColor } from '@rotki/common';
import { useTagsApi } from '@/composables/api/tags';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useSessionMetadataStore } from '@/store/session/metadata';
import { logger } from '@/utils/logging';

interface UseTagOperationsReturn {
  addTag: (tag: Tag) => Promise<ActionStatus>;
  attemptTagCreation: (tag: string, backgroundColor?: string) => Promise<boolean>;
  deleteTag: (name: string) => Promise<void>;
  editTag: (tag: Tag, originalName: string) => Promise<ActionStatus>;
  fetchTags: () => Promise<void>;
}

export function useTagOperations(): UseTagOperationsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { queryAddTag, queryDeleteTag, queryEditTag, queryTags } = useTagsApi();
  const { removeTag, renameTag } = useBlockchainAccountsStore();
  const { showErrorMessage } = useNotifications();
  const { allTags, tags } = storeToRefs(useSessionMetadataStore());

  async function addTag(tag: Tag): Promise<ActionStatus> {
    try {
      set(allTags, await queryAddTag(tag));
      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      showErrorMessage(t('actions.session.tag_add.error.title'), message);
      return { message, success: false };
    }
  }

  async function editTag(tag: Tag, originalName: string): Promise<ActionStatus> {
    try {
      set(allTags, await queryEditTag(tag, originalName));
      if (originalName !== tag.name)
        renameTag(originalName, tag.name);

      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      showErrorMessage(t('actions.session.tag_edit.error.title'), message);
      return { message, success: false };
    }
  }

  async function deleteTag(name: string): Promise<void> {
    try {
      set(allTags, await queryDeleteTag(name));
      removeTag(name);
    }
    catch (error: unknown) {
      showErrorMessage(t('actions.session.tag_delete.error.title'), getErrorMessage(error));
    }
  }

  async function fetchTags(): Promise<void> {
    try {
      set(allTags, await queryTags());
    }
    catch (error: unknown) {
      logger.error('Tags fetch failed', error);
    }
  }

  function tagExists(tagName: string): boolean {
    return get(tags).some(({ name }) => name === tagName);
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
  }

  return {
    addTag,
    attemptTagCreation,
    deleteTag,
    editTag,
    fetchTags,
  };
}
