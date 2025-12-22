import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import { type Tag, Tags } from '@/types/tags';

interface UseTagsApiReturn {
  queryTags: () => Promise<Tags>;
  queryAddTag: (tag: Tag) => Promise<Tags>;
  queryEditTag: (tag: Tag, originalName: string) => Promise<Tags>;
  queryDeleteTag: (tagName: string) => Promise<Tags>;
}

interface TagEditPayload {
  name: string;
  newName?: string;
  description: string | null;
  backgroundColor: string;
  foregroundColor: string;
}

export function useTagsApi(): UseTagsApiReturn {
  const queryTags = async (): Promise<Tags> => {
    const data = await api.get<Tags>('/tags', {
      validStatuses: VALID_WITH_SESSION_STATUS,
      skipRootCamelCase: true,
    });

    return Tags.parse(data);
  };

  const queryAddTag = async (tag: Tag): Promise<Tags> => {
    const data = await api.put<Tags>('/tags', tag, {
      skipRootCamelCase: true,
    });

    return Tags.parse(data);
  };

  const queryEditTag = async (tag: Tag, originalName: string): Promise<Tags> => {
    const payload: TagEditPayload = {
      backgroundColor: tag.backgroundColor,
      description: tag.description,
      foregroundColor: tag.foregroundColor,
      name: originalName,
    };

    if (originalName !== tag.name)
      payload.newName = tag.name;

    const data = await api.patch<Tags>('/tags', payload, {
      skipRootCamelCase: true,
    });

    return Tags.parse(data);
  };

  const queryDeleteTag = async (tagName: string): Promise<Tags> => {
    const data = await api.delete<Tags>('/tags', {
      body: {
        name: tagName,
      },
      skipRootCamelCase: true,
    });

    return Tags.parse(data);
  };

  return {
    queryAddTag,
    queryDeleteTag,
    queryEditTag,
    queryTags,
  };
}
