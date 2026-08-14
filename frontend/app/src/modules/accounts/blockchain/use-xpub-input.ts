import type { MaybeRefOrGetter, Ref } from 'vue';
import type { XpubPayload } from '@/modules/accounts/blockchain-accounts';
import type { BtcChains } from '@/modules/core/common/chains';
import { Blockchain } from '@rotki/common';
import { type DetectionResult, detectXpubType, getKeyType, getPrefix, XpubPrefix } from '@/modules/accounts/xpub';

/** The two fields the user types into. The payload is assembled from them and the chosen prefix. */
export interface XpubFormState {
  derivationPath: string;
  xpub: string;
}

interface XpubInputOptions {
  readonly blockchain: MaybeRefOrGetter<BtcChains>;
  /** An existing account is shown read-only, where the type is stated rather than detected. */
  readonly disabled: MaybeRefOrGetter<boolean>;
  /** Pasting a plain address rather than a key is handled by the parent, which switches mode. */
  readonly onAddressDetected: (address: string) => void;
}

interface XpubInputReturn {
  readonly prefix: Readonly<Ref<XpubPrefix>>;
  readonly detectedType: Readonly<Ref<DetectionResult | undefined>>;
  readonly showDisambiguation: Readonly<Ref<boolean>>;
  /** Records the address type the user picked when the key alone does not say which it is. */
  readonly resolveDisambiguation: (choice: XpubPrefix) => void;
}

/** Bitcoin cash has no segwit, so a bare key there can only be legacy. */
function defaultPrefixFor(chain: BtcChains): XpubPrefix {
  return chain === Blockchain.BCH ? XpubPrefix.XPUB : XpubPrefix.ZPUB;
}

/** The apostrophes and the trailing separator are ours to drop; the backend takes neither. */
function normalizeDerivationPath(path: string): string {
  return path.replace(/'/g, '').replace(/\/$/, '');
}

function samePayload(a: XpubPayload | undefined, b: XpubPayload | undefined): boolean {
  return a?.xpub === b?.xpub
    && a?.xpubType === b?.xpubType
    && a?.derivationPath === b?.derivationPath;
}

/**
 * Keeps the xpub payload and the fields it is typed into in step.
 *
 * The address type is read off the key where its prefix says which one it is, and asked for where
 * it does not. It is not part of the form state, because the user picks it from a prompt rather
 * than typing it, but it does belong to the payload, so a change to it rewrites that.
 */
export function useXpubInput(
  state: XpubFormState,
  model: Ref<XpubPayload | undefined>,
  options: XpubInputOptions,
): XpubInputReturn {
  const { blockchain, disabled, onAddressDetected } = options;

  const prefix = shallowRef<XpubPrefix>(defaultPrefixFor(toValue(blockchain)));
  const detectedType = shallowRef<DetectionResult>();
  const showDisambiguation = shallowRef<boolean>(false);

  function runDetection(value: string): void {
    const result = detectXpubType(value);
    set(detectedType, result);
    set(showDisambiguation, false);

    if (result === 'address') {
      onAddressDetected(value.trim());
      return;
    }

    if (result === XpubPrefix.YPUB || result === XpubPrefix.ZPUB) {
      set(prefix, result);
      return;
    }

    if (result === 'ambiguous') {
      set(prefix, defaultPrefixFor(toValue(blockchain)));
      if (toValue(blockchain) !== Blockchain.BCH)
        set(showDisambiguation, true);
    }
  }

  // The payload is the source of truth, so what it holds is written back into the fields. The
  // derivation path is only overwritten when it means something different, or every apostrophe
  // would be stripped from under the user as they type.
  watchImmediate(model, (payload) => {
    state.xpub = payload?.xpub ?? '';

    const path = payload?.derivationPath ?? '';
    if (normalizeDerivationPath(state.derivationPath) !== path)
      state.derivationPath = path;

    if (!payload?.xpubType)
      return;

    const detected = getPrefix(payload.xpubType);
    set(prefix, detected);
    // A read-only field detects nothing, so the type it was saved with is stated instead.
    if (toValue(disabled) && payload.xpub)
      set(detectedType, detected);
  });

  watch(() => toValue(blockchain), (chain) => {
    set(prefix, defaultPrefixFor(chain));
  });

  watch(() => state.xpub, (key) => {
    if (!key) {
      set(detectedType, undefined);
      set(showDisambiguation, false);
      return;
    }
    runDetection(key);
  });

  watch([
    prefix,
    (): string => state.xpub,
    (): string => state.derivationPath,
  ], ([prefix, key, path]): void => {
    const next: XpubPayload | undefined = key
      ? {
          derivationPath: normalizeDerivationPath(path),
          xpub: key.trim(),
          xpubType: getKeyType(prefix),
        }
      : undefined;

    if (!samePayload(get(model), next))
      set(model, next);
  });

  return {
    detectedType: readonly(detectedType),
    prefix: readonly(prefix),
    resolveDisambiguation: (choice: XpubPrefix): void => {
      set(prefix, choice);
      set(detectedType, choice);
    },
    showDisambiguation: readonly(showDisambiguation),
  };
}
