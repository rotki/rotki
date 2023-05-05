import { type ActionResult } from '@rotki/common/lib/data';
import {
  noRootCamelCaseTransformer,
  snakeCaseTransformer
} from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import { type Tag, Tags } from '@/types/tags';

export const useTagsApi = () => {
  const queryTags = async (): Promise<Tags> => {
    const response = await api.instance.get<ActionResult<Tags>>('/tags', {
      validateStatus: validWithSessionStatus
    });

    const data = handleResponse(response);
    return Tags.parse(noRootCamelCaseTransformer(data));
  };

  const queryAddTag = async (tag: Tag): Promise<Tags> => {
    const response = await api.instance.put<ActionResult<Tags>>(
      '/tags',
      snakeCaseTransformer(tag),
      {
        validateStatus: validStatus
      }
    );

    const data = handleResponse(response);
    return Tags.parse(noRootCamelCaseTransformer(data));
  };

  const queryEditTag = async (tag: Tag): Promise<Tags> => {
    const response = await api.instance.patch<ActionResult<Tags>>(
      '/tags',
      snakeCaseTransformer(tag),
      {
        validateStatus: validStatus
      }
    );

    const data = handleResponse(response);
    return Tags.parse(noRootCamelCaseTransformer(data));
  };

  const queryDeleteTag = async (tagName: string): Promise<Tags> => {
    const response = await api.instance.delete<ActionResult<Tags>>('/tags', {
      data: {
        name: tagName
      },
      validateStatus: validStatus
    });

    const data = handleResponse(response);
    return Tags.parse(noRootCamelCaseTransformer(data));
  };

  return {
    queryTags,
    queryAddTag,
    queryEditTag,
    queryDeleteTag
  };
};
