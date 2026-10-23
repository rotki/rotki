import { describe, expect, it } from 'vitest';
import { gnosisPayNonceActivity, gnosisPayVerifyActivity } from './gnosis-pay.activity';

describe('gnosis pay activity ids', () => {
  it('should give the nonce fetch and the verification their fixed ids', () => {
    expect(gnosisPayNonceActivity.id()).toBe('gnosis-pay:nonce');
    expect(gnosisPayVerifyActivity.id()).toBe('gnosis-pay:verify');
  });
});
