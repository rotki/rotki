import type { RouteLocationRaw } from 'vue-router';
import { pslSuffixes } from '@/data/psl';
import { Routes } from '@/router/routes';
import { logger } from '@/utils/logging';
import { etherscanLink, externalLinks } from '@shared/external-links';

export function getDomain(str: string): string {
  const pattern = /^(?:https?:)?(?:\/\/)?(?:[^\n@]+@)?(?:www\.)?([^\n/:]+)/;
  const exec = pattern.exec(str);

  const withSubdomain = exec?.[1];

  if (!withSubdomain)
    return str;

  const parts = withSubdomain.split('.');
  const length = parts.length;
  let i = length - 1;
  let domain = withSubdomain;

  while (i > 0) {
    const used = parts.slice(-i).join('.');
    const found = pslSuffixes.has(used);

    if (found)
      break;

    domain = used;
    i -= 1;
  }

  return domain;
}

interface ExternalUrl { external: string; route: RouteLocationRaw }

/**
 * Returns the registration url of a specified Etherscan registration link, and the page to fill it
 * @returns {{external: string, route: RouteLocationRaw} | undefined}
 */
export function getEtherScanRegisterUrl(): ExternalUrl | undefined {
  return {
    external: etherscanLink,
    route: {
      path: Routes.API_KEYS_EXTERNAL_SERVICES.toString(),
      query: { service: 'etherscan' },
    },
  };
}

export function getTheGraphRegisterUrl(): ExternalUrl {
  return {
    external: externalLinks.applyTheGraphApiKey,
    route: {
      path: Routes.API_KEYS_EXTERNAL_SERVICES.toString(),
      query: { service: 'thegraph' },
    },
  };
}

/**
 * Returns the registration url of a specified service and a path to the local page
 * @param {string} service
 * @returns {undefined | {external: string, route: RouteLocationRaw}}
 */
export function getServiceRegisterUrl(service: string): ExternalUrl | undefined {
  switch (service) {
    case 'etherscan':
      return getEtherScanRegisterUrl();
    case 'thegraph':
      return getTheGraphRegisterUrl();
    default:
      logger.warn(`Unsupported service: '${service}'`);
      return undefined;
  }
}
