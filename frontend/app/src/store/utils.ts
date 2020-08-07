import { Commit } from 'vuex';
import { Message } from '@/store/store';

export function showError(commit: Commit, description: string, title?: string) {
  commit(
    'setMessage',
    {
      title: title ?? 'Error',
      description: description || '',
      success: false
    } as Message,
    { root: true }
  );
}
