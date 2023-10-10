import { type ActionResult } from '@rotki/common/lib/data';
import { omit } from 'lodash-es';
import {
  type AccountingRule,
  type AccountingRuleEntry,
  AccountingRuleEntryCollectionResponse,
  type AccountingRuleRequestPayload,
  type DeleteAccountingRulePayload
} from '@/types/settings/accounting';
import { type CollectionResponse } from '@/types/collection';
import { handleResponse, validStatus } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { snakeCaseTransformer } from '@/services/axios-tranformers';

export const useAccountingApi = () => {
  const fetchAccountingRules = async (
    payload: AccountingRuleRequestPayload
  ): Promise<CollectionResponse<AccountingRuleEntry>> => {
    const response = await api.instance.post<
      ActionResult<CollectionResponse<AccountingRuleEntry>>
    >(
      '/accounting/rules',
      snakeCaseTransformer(omit(payload, ['orderByAttributes', 'ascending'])),
      {
        validateStatus: validStatus
      }
    );

    return AccountingRuleEntryCollectionResponse.parse(
      handleResponse(response)
    );
  };

  const addAccountingRule = async (
    payload: AccountingRule
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/accounting/rules',
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const editAccountingRule = async (
    payload: AccountingRuleEntry
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/accounting/rules',
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteAccountingRule = async (
    payload: DeleteAccountingRulePayload
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/accounting/rules',
      {
        data: snakeCaseTransformer(payload),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    fetchAccountingRules,
    addAccountingRule,
    editAccountingRule,
    deleteAccountingRule
  };
};
