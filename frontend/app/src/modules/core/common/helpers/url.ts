import type { RouteLocationRaw } from 'vue-router';
import { blockscoutLink, etherscanLink, externalLinks } from '@shared/external-links';
import { logger } from '@/modules/core/common/logging/logging';
import { pslSuffixes } from '@/modules/core/common/psl';

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
 * @returns where to register for an Etherscan key, and the settings page the key is filled in on.
 */
function getEtherScanRegisterUrl(): ExternalUrl | undefined {
  return {
    external: etherscanLink,
    route: {
      name: '/api-keys/external/',
      query: { service: 'etherscan' },
    },
  };
}

function getBlockscoutRegisterUrl(): ExternalUrl {
  return {
    external: blockscoutLink,
    route: {
      name: '/api-keys/external/',
      query: { service: 'blockscout' },
    },
  };
}

function getTheGraphRegisterUrl(): ExternalUrl {
  return {
    external: externalLinks.applyTheGraphApiKey,
    route: {
      name: '/api-keys/external/',
      query: { service: 'thegraph' },
    },
  };
}

function getHeliusRegisterUrl(): ExternalUrl {
  return {
    external: 'https://dev.helius.xyz/dashboard/app',
    route: {
      name: '/api-keys/external/',
      query: { service: 'helius' },
    },
  };
}

function getBeaconchainRegisterUrl(): ExternalUrl {
  return {
    external: externalLinks.beaconChainApiKey,
    route: {
      name: '/api-keys/external/',
      query: { service: 'beaconchain' },
    },
  };
}

/**
 * The registration URL of an external service, paired with the local page that explains it.
 *
 * @returns `undefined` for a service that needs no registration
 */
export function getServiceRegisterUrl(service: string): ExternalUrl | undefined {
  switch (service) {
    case 'etherscan':
      return getEtherScanRegisterUrl();
    case 'blockscout':
      return getBlockscoutRegisterUrl();
    case 'thegraph':
      return getTheGraphRegisterUrl();
    case 'helius':
      return getHeliusRegisterUrl();
    case 'beaconchain':
      return getBeaconchainRegisterUrl();
    default:
      logger.warn(`Unsupported service: '${service}'`);
      return undefined;
  }
}
