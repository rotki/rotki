import store, { Message } from '@/store/store';

export function showError(description: string, title?: string) {
  const message = {
    title: title ?? 'Error',
    description: description || '',
    success: false
  };
  store.commit('setMessage', message);
}

export function showMessage(description: string, title?: string): void {
  const message: Message = {
    title: title ?? 'Success',
    description,
    success: true
  };
  store.commit('setMessage', message);
}
