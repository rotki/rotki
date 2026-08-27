import { describe, expect, it } from 'vitest';
import { changePasswordSchema, emptyChangePasswordState } from '@/modules/settings/data-security/change-password-form';

const messages = {
  emptyConfirmation: 'empty-confirmation',
  emptyPassword: 'empty-password',
  mismatch: 'mismatch',
};

const schema = changePasswordSchema(messages);

function issuesFor(state: Partial<Record<string, string>>): [string, string][] {
  const result = schema.safeParse({ ...emptyChangePasswordState(), ...state });
  if (result.success)
    return [];

  return result.error.issues.map(issue => [issue.path.join('.'), issue.message]);
}

describe('changePasswordSchema', () => {
  it('should accept a filled, matching pair', () => {
    expect(issuesFor({ currentPassword: 'old', newPassword: 'new', newPasswordConfirm: 'new' })).toStrictEqual([]);
  });

  it('should report a blank confirmation as both empty and mismatched', () => {
    expect(issuesFor({ currentPassword: 'old', newPassword: 'new' })).toStrictEqual([
      ['newPasswordConfirm', 'empty-confirmation'],
      ['newPasswordConfirm', 'mismatch'],
    ]);
  });

  it('should report a mismatch alone when both halves are filled', () => {
    expect(issuesFor({ currentPassword: 'old', newPassword: 'new', newPasswordConfirm: 'other' })).toStrictEqual([
      ['newPasswordConfirm', 'mismatch'],
    ]);
  });

  it('should treat a whitespace-only value as missing', () => {
    expect(issuesFor({ currentPassword: '   ', newPassword: '  ', newPasswordConfirm: '  ' })).toStrictEqual([
      ['currentPassword', 'empty-password'],
      ['newPassword', 'empty-password'],
      ['newPasswordConfirm', 'empty-confirmation'],
    ]);
  });

  it('should keep each message under the field it names', () => {
    expect(issuesFor({ newPassword: 'new', newPasswordConfirm: 'new' })).toStrictEqual([
      ['currentPassword', 'empty-password'],
    ]);
  });
});
