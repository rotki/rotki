import type { ActionStatus } from '@/modules/core/common/action';
import type { Tag } from '@/modules/tags/tags';
import { invertColor, randomColor } from '@rotki/common';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useTagsApi } from '@/modules/tags/use-tags-api';

interface UseTagOperationsReturn {
  addTag: (tag: Tag) => Promise<ActionStatus>;
  attemptTagCreation: (tag: string, backgroundColor?: string) => Promise<ActionStatus>;
  deleteTag: (name: string) => Promise<void>;
  editTag: (tag: Tag, originalName: string) => Promise<ActionStatus>;
  fetchTags: () => Promise<void>;
}

export function useTagOperations(): UseTagOperationsReturn {
  const { queryAddTag, queryDeleteTag, queryEditTag, queryTags } = useTagsApi();
  const { removeTag, renameTag } = useBlockchainAccountsStore();
  const { allTags, tags } = storeToRefs(useSessionMetadataStore());

  /**
   * Adds a tag.
   *
   * @returns The outcome, carrying the error message on failure for the caller to show.
   */
  async function addTag(tag: Tag): Promise<ActionStatus> {
    try {
      set(allTags, await queryAddTag(tag));
      return { success: true };
    }
    catch (error: unknown) {
      return { message: getErrorMessage(error), success: false };
    }
  }

  /**
   * Edits a tag, renaming it on the accounts that carry it when its name changed.
   *
   * @returns The outcome, carrying the error message on failure for the caller to show.
   */
  async function editTag(tag: Tag, originalName: string): Promise<ActionStatus> {
    try {
      set(allTags, await queryEditTag(tag, originalName));
      if (originalName !== tag.name)
        renameTag(originalName, tag.name);

      return { success: true };
    }
    catch (error: unknown) {
      return { message: getErrorMessage(error), success: false };
    }
  }

  /**
   * Deletes a tag and drops it from the accounts that carry it.
   *
   * @throws The request's error, for the caller to name beside the tag it came from.
   */
  async function deleteTag(name: string): Promise<void> {
    set(allTags, await queryDeleteTag(name));
    removeTag(name);
  }

  async function fetchTags(): Promise<void> {
    try {
      set(allTags, await queryTags());
    }
    catch (error: unknown) {
      if (!isRequestCancellation(error))
        logger.error('Tags fetch failed', error);
    }
  }

  function tagExists(tagName: string): boolean {
    return get(tags).some(({ name }) => name === tagName);
  }

  /**
   * Creates a tag unless one with that name already exists.
   *
   * @returns Success when the tag exists afterwards, or the reason it could not be created.
   */
  async function attemptTagCreation(tag: string, backgroundColor?: string): Promise<ActionStatus> {
    if (tagExists(tag))
      return { success: true };

    const bgColor = backgroundColor ?? randomColor();
    const fgColor = invertColor(bgColor);

    const newTag: Tag = {
      backgroundColor: bgColor,
      description: '',
      foregroundColor: fgColor,
      name: tag,
    };

    return addTag(newTag);
  }

  return {
    addTag,
    attemptTagCreation,
    deleteTag,
    editTag,
    fetchTags,
  };
}
