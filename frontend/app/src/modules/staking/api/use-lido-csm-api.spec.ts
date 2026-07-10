import type { LidoCsmNodeOperator } from '@/modules/staking/staking-types';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  VALID_STATUS_CODES,
  VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITH_SESSION_STATUS,
} from '@/modules/core/api/utils';
import { useLidoCsmApi } from '@/modules/staking/api/use-lido-csm-api';

const { mockDelete, mockGet, mockPost, mockPut } = vi.hoisted(() => ({
  mockDelete: vi.fn(),
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
}));

vi.mock('@/modules/core/api', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/api')>(),
  api: {
    delete: mockDelete,
    get: mockGet,
    post: mockPost,
    put: mockPut,
  },
}));

function operator(): LidoCsmNodeOperator {
  return { address: '0xabc', metrics: null, nodeOperatorId: 1 };
}

function response(message?: string): { message?: string; result: LidoCsmNodeOperator[] } {
  return { message, result: [operator()] };
}

describe('useLidoCsmApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue(response('ok'));
    mockPut.mockResolvedValue(response('added'));
    mockDelete.mockResolvedValue(response('deleted'));
    mockPost.mockResolvedValue(response('refreshed'));
  });

  it('should list node operators', async () => {
    const { listNodeOperators } = useLidoCsmApi();
    const result = await listNodeOperators();

    expect(mockGet).toHaveBeenCalledWith('/lido-csm/node-operators', {
      skipResultUnwrap: true,
      validStatuses: VALID_WITH_SESSION_STATUS,
    });
    expect(result).toEqual({ entries: [operator()], message: 'ok' });
  });

  it('should add a node operator with a schema-validated payload', async () => {
    const { addNodeOperator } = useLidoCsmApi();
    const result = await addNodeOperator({ address: '0xabc', nodeOperatorId: 2 });

    expect(mockPut).toHaveBeenCalledWith('/lido-csm/node-operators', { address: '0xabc', nodeOperatorId: 2 }, {
      skipResultUnwrap: true,
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    expect(result.message).toBe('added');
  });

  it('should strip unknown fields from the payload before sending', async () => {
    const { addNodeOperator } = useLidoCsmApi();
    const payload = { address: '0xabc', extra: 'nope', nodeOperatorId: 3 };
    await addNodeOperator(payload);

    expect(mockPut).toHaveBeenCalledWith('/lido-csm/node-operators', { address: '0xabc', nodeOperatorId: 3 }, expect.any(Object));
  });

  it('should delete a node operator using the payload as the request body', async () => {
    const { deleteNodeOperator } = useLidoCsmApi();
    await deleteNodeOperator({ address: '0xabc', nodeOperatorId: 4 });

    expect(mockDelete).toHaveBeenCalledWith('/lido-csm/node-operators', {
      body: { address: '0xabc', nodeOperatorId: 4 },
      skipResultUnwrap: true,
      validStatuses: VALID_STATUS_CODES,
    });
  });

  it('should refresh metrics via the metrics path', async () => {
    const { refreshMetrics } = useLidoCsmApi();
    const result = await refreshMetrics();

    expect(mockPost).toHaveBeenCalledWith('/lido-csm/metrics', undefined, {
      skipResultUnwrap: true,
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    expect(result.message).toBe('refreshed');
  });

  it('should default the message to an empty string when absent', async () => {
    mockGet.mockResolvedValue(response(undefined));
    const { listNodeOperators } = useLidoCsmApi();
    const result = await listNodeOperators();
    expect(result.message).toBe('');
  });
});
