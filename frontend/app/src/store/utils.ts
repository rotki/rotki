import { Commit } from 'vuex';
import i18n from '@/i18n';
import { Section, Status } from '@/store/const';
import store from '@/store/store';
import { Message, StatusPayload } from '@/store/types';

export function showError(description: string, title?: string) {
  const message = {
    title: title ?? i18n.t('message.error.title').toString(),
    description: description || '',
    success: false
  };
  store.commit('setMessage', message);
}

export function showMessage(description: string, title?: string): void {
  const message: Message = {
    title: title ?? i18n.t('message.success.title').toString(),
    description,
    success: true
  };
  store.commit('setMessage', message);
}

export const setStatus: (
  newStatus: Status,
  section: Section,
  status: (section: Section) => Status,
  commit: Commit
) => void = (newStatus, section, status, commit) => {
  if (status(section) === newStatus) {
    return;
  }
  const payload: StatusPayload = {
    section: section,
    status: newStatus
  };
  commit('setStatus', payload, { root: true });
};

export function isLoading(status: Status): boolean {
  return (
    status === Status.LOADING ||
    status === Status.PARTIALLY_LOADED ||
    status === Status.REFRESHING
  );
}
