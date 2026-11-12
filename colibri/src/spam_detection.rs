//! Advisory token-spam scoring from the exported spam-detection MLP.
//!
//! The model is the provenance-disabled 59-input MLP exported by the offline ``spam_nn``
//! experiment. Inference is local only: no network and no remote RPC. The exported
//! artifact lives in ``colibri/data`` and is embedded in the binary, then parsed and
//! validated once per process.
//!
//! This is a port of the Python reference (``spam_nn/features.py`` and ``spam_nn/model.py``).
//! That reference, the training pipeline and the generator of
//! ``tests/fixtures/spam_detection_parity.json`` live in
//! <https://gist.github.com/yabirgb/6811c4337f3c1648a6115b253b1b78ad>. Regenerate the
//! fixture after retraining or changing a feature, then keep this port in step with it.
//!
//! The score is an advisory model estimate, not a spam verdict and not a guarantee of
//! authenticity. The experiment trained on weak labels and sampled controls; it is not
//! calibrated for production spam prevalence, and its observed control flag rate does
//! not establish a safe automatic-hiding threshold.
//!
//! Unicode behavior (NFKC, full case folding, general categories and character names)
//! matches Python's ``unicodedata`` and ``str.casefold`` for the crate's Unicode
//! version instead of approximating it with ASCII lowercasing.

use std::collections::{HashMap, HashSet};
use std::sync::LazyLock;

use caseless::default_case_fold_str;
use regex::Regex;
use serde::{Deserialize, Serialize};
use unicode_general_category::{get_general_category, GeneralCategory};
use unicode_normalization::UnicodeNormalization;

const SPAM_MODEL_JSON: &str = include_str!("../data/spam_mlp_no_provenance.json");

/// Common Greek/Cyrillic Latin lookalikes, applied after NFKC and casefold.
const CONFUSABLES: [(char, char); 36] = [
    ('\u{0430}', 'a'),
    ('\u{0432}', 'b'),
    ('\u{0441}', 'c'),
    ('\u{0501}', 'd'),
    ('\u{0435}', 'e'),
    ('\u{04bb}', 'h'),
    ('\u{0456}', 'i'),
    ('\u{0458}', 'j'),
    ('\u{043a}', 'k'),
    ('\u{043c}', 'm'),
    ('\u{043d}', 'h'),
    ('\u{043e}', 'o'),
    ('\u{0440}', 'p'),
    ('\u{0455}', 's'),
    ('\u{0442}', 't'),
    ('\u{0443}', 'y'),
    ('\u{0445}', 'x'),
    ('\u{051d}', 'w'),
    ('\u{04cf}', 'l'),
    ('\u{051b}', 'q'),
    ('\u{03b1}', 'a'),
    ('\u{03b2}', 'b'),
    ('\u{03f2}', 'c'),
    ('\u{03b4}', 'd'),
    ('\u{03b5}', 'e'),
    ('\u{03b7}', 'h'),
    ('\u{03b9}', 'i'),
    ('\u{03ba}', 'k'),
    ('\u{03bc}', 'm'),
    ('\u{03bd}', 'v'),
    ('\u{03bf}', 'o'),
    ('\u{03c1}', 'p'),
    ('\u{03c4}', 't'),
    ('\u{03c5}', 'u'),
    ('\u{03c7}', 'x'),
    ('\u{03f3}', 'j'),
];

const CANONICAL_SYMBOLS: [&str; 13] = [
    "eth", "usdc", "usdt", "btc", "wbtc", "weth", "dai", "link", "uni", "aave", "matic", "bnb",
    "sol",
];

static URL: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?i)(?:https?://|www\.|(?:t|telegram)\.me/|(?:(?:^|[^\p{L}\p{N}_])[a-z0-9]|[\p{L}\p{N}_]-)[a-z0-9-]*\.(?:com|net|org|io|xyz|app|finance|vip|vc)(?:$|[^\p{L}\p{N}_]))",
    )
    .expect("spam detection URL pattern is valid")
});

static PROMO: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)(?:^|[^\p{L}\p{N}_])(?:airdrop|claim|reward|bonus|giveaway|free|voucher|redeem|visit|win)(?:$|[^\p{L}\p{N}_])")
        .expect("spam detection promotion pattern is valid")
});

static CONTACT: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)(?:telegram|whatsapp|wechat|discord|微信|(?:^|[^\p{L}\p{N}_])qq(?:$|[^\p{L}\p{N}_])|t\.me/)")
        .expect("spam detection contact pattern is valid")
});

/// Context inputs, in model-feature order, with the cap applied before the transform.
const CONTEXT: [(&str, f64); 10] = [
    ("tx_count", 1_000_000_000.0),
    ("mean_log_count", 1_000_000.0),
    ("max_log_count", 1_000_000.0),
    ("mean_token_transfer_count", 1_000_000.0),
    ("max_token_transfer_count", 1_000_000.0),
    ("min_prior_tx_gap_seconds", 315_576_000.0),
    ("known_origin_fraction", 1.0),
    ("outgoing_fraction", 1.0),
    ("in_packaged_globaldb", 1.0),
    ("in_collection", 1.0),
];

const TEXT_FEATURES: [&str; 17] = [
    "length_log1p",
    "nonascii_fraction",
    "invisible_fraction",
    "combining_fraction",
    "digit_fraction",
    "punctuation_fraction",
    "whitespace_fraction",
    "mixed_scripts",
    "script_count",
    "nfkc_changed",
    "skeleton_changed",
    "has_url",
    "has_promotion",
    "has_contact",
    "has_currency_sign",
    "has_percent",
    "exclamation_count",
];

const PROVENANCE_FEATURE_PREFIXES: [&str; 2] =
    ["context_in_packaged_globaldb_", "context_in_collection_"];

static FEATURE_NAMES: LazyLock<Vec<String>> = LazyLock::new(|| {
    let mut names = Vec::with_capacity(59);
    for field in ["name", "symbol"] {
        for feature in TEXT_FEATURES {
            names.push(format!("{field}_{feature}"));
        }
    }
    names.extend(
        [
            "symbol_canonical_match",
            "symbol_confusable_canonical_match",
            "name_symbol_equal",
            "decimals_scaled",
            "decimals_missing",
        ]
        .map(String::from),
    );
    for (key, _) in CONTEXT {
        for suffix in ["value", "missing"] {
            names.push(format!("context_{key}_{suffix}"));
        }
    }
    names
});

/// Numeric context for one token. A missing key, or a value that is not a finite
/// non-negative number, is `None`. Boolean provenance flags are represented as
/// `Some(1.0)`/`Some(0.0)` so that they keep Python's "present / not present" meaning.
pub(crate) type SpamContext = HashMap<String, Option<f64>>;

/// The bounded token metadata the model consumes.
#[derive(Debug, Clone, Default)]
pub(crate) struct SpamRecord {
    pub name: String,
    pub symbol: String,
    pub decimals: Option<u32>,
    pub context: SpamContext,
}

#[derive(Debug, Deserialize)]
struct SpamModelCalibration {
    slope: f64,
    intercept: f64,
}

#[derive(Debug, Deserialize)]
struct SpamModel {
    format_version: u32,
    features: Vec<String>,
    mean: Vec<f64>,
    scale: Vec<f64>,
    reference: Vec<f64>,
    w1: Vec<Vec<f64>>,
    b1: Vec<f64>,
    w2: Vec<f64>,
    b2: f64,
    calibration: SpamModelCalibration,
    threshold: f64,
    exclude_provenance: bool,
}

/// One local-sensitivity explanation entry.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub(crate) struct SpamModelReason {
    pub feature: String,
    pub value: f64,
    pub probability_delta: f64,
}

/// The part of the token a [`SpamSignal`] describes.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub(crate) enum SpamSignalField {
    Name,
    Symbol,
    Context,
}

/// What was observed. Consumers translate the code; none of them is a spam verdict
/// or an authenticity claim on its own.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub(crate) enum SpamSignalCode {
    NonAscii,
    InvisibleCharacters,
    CombiningMarks,
    MixedScripts,
    Url,
    Promotion,
    CommonSymbol,
    LookalikeSymbol,
    KnownOriginUnavailable,
    /// `value` is the maximum same-token Transfer count within one transaction.
    MaxTokenTransfers,
    /// `value` is the mean same-token Transfer count per observed transaction.
    MeanTokenTransfers,
    InPackagedGlobaldb,
    NotInPackagedGlobaldb,
    InCollection,
    NotInCollection,
}

/// One observed metadata fact behind a prediction.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub(crate) struct SpamSignal {
    pub field: SpamSignalField,
    pub code: SpamSignalCode,
    /// Only set for the transfer-count codes.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub value: Option<f64>,
}

impl SpamSignal {
    fn new(field: SpamSignalField, code: SpamSignalCode) -> Self {
        Self {
            field,
            code,
            value: None,
        }
    }
}

/// The advisory model estimate for one token.
#[derive(Debug, Clone, Serialize, PartialEq)]
pub(crate) struct SpamPrediction {
    pub spam_probability: f64,
    pub flagged: bool,
    pub threshold: f64,
    pub observed_signals: Vec<SpamSignal>,
    pub model_reasons: Vec<SpamModelReason>,
}

/// Python's `str.isspace()` set, which also contains U+001C..U+001F.
fn python_isspace(char: char) -> bool {
    char.is_whitespace() || matches!(char as u32, 0x1c..=0x1f)
}

/// Python's `str.strip()` whitespace set.
fn python_strip(text: &str) -> &str {
    text.trim_matches(python_isspace)
}

/// Python's `str.split()` with no separator: split on whitespace runs.
fn python_words(text: &str) -> impl Iterator<Item = &str> {
    text.split(python_isspace).filter(|word| !word.is_empty())
}

/// NFKC compatibility normalization.
fn nfkc(text: &str) -> String {
    text.nfkc().collect()
}

/// Python's `str.casefold()`: full, locale-independent case folding.
fn casefold(text: &str) -> String {
    default_case_fold_str(text)
}

fn is_letter(category: GeneralCategory) -> bool {
    matches!(
        category,
        GeneralCategory::UppercaseLetter
            | GeneralCategory::LowercaseLetter
            | GeneralCategory::TitlecaseLetter
            | GeneralCategory::ModifierLetter
            | GeneralCategory::OtherLetter
    )
}

fn is_combining(category: GeneralCategory) -> bool {
    matches!(
        category,
        GeneralCategory::NonspacingMark
            | GeneralCategory::SpacingMark
            | GeneralCategory::EnclosingMark
    )
}

fn is_punctuation(category: GeneralCategory) -> bool {
    matches!(
        category,
        GeneralCategory::ConnectorPunctuation
            | GeneralCategory::DashPunctuation
            | GeneralCategory::ClosePunctuation
            | GeneralCategory::FinalPunctuation
            | GeneralCategory::InitialPunctuation
            | GeneralCategory::OtherPunctuation
            | GeneralCategory::OpenPunctuation
    )
}

/// Unicode chars with `Numeric_Type=Digit` that are not `Decimal_Number`, which Python's
/// `str.isdigit()` accepts but no Rust standard-library predicate exposes.
const DIGIT_OTHER_NUMBER_RANGES: [(u32, u32); 20] = [
    (0xb2, 0xb3),
    (0xb9, 0xb9),
    (0x1369, 0x1371),
    (0x19da, 0x19da),
    (0x2070, 0x2070),
    (0x2074, 0x2079),
    (0x2080, 0x2089),
    (0x2460, 0x2468),
    (0x2474, 0x247c),
    (0x2488, 0x2490),
    (0x24ea, 0x24ea),
    (0x24f5, 0x24fd),
    (0x24ff, 0x24ff),
    (0x2776, 0x277e),
    (0x2780, 0x2788),
    (0x278a, 0x2792),
    (0x10a40, 0x10a43),
    (0x10e60, 0x10e68),
    (0x11052, 0x1105a),
    (0x1f100, 0x1f10a),
];

/// Python's `str.isdigit()`.
fn is_digit(char: char, category: GeneralCategory) -> bool {
    match category {
        GeneralCategory::DecimalNumber => true,
        GeneralCategory::OtherNumber => {
            let code = char as u32;
            DIGIT_OTHER_NUMBER_RANGES
                .iter()
                .any(|(start, end)| (*start..=*end).contains(&code))
        }
        _ => false,
    }
}

fn is_invisible(char: char) -> bool {
    let category = get_general_category(char);
    category == GeneralCategory::Format
        || matches!(char, '\u{034f}' | '\u{180b}' | '\u{180c}' | '\u{180d}')
        || unicode_name(char).is_some_and(|name| name.contains("VARIATION SELECTOR"))
}

fn unicode_name(char: char) -> Option<String> {
    unicode_names2::name(char).map(|name| name.to_string())
}

fn normalized(text: &str) -> String {
    let folded = casefold(&nfkc(text));
    python_words(&folded).collect::<Vec<_>>().join(" ")
}

fn confusable(char: char) -> Option<char> {
    CONFUSABLES
        .iter()
        .find_map(|(source, target)| (*source == char).then_some(*target))
}

/// Case-folded compatibility/visual key with invisible marks and lookalikes folded.
pub(crate) fn skeleton(text: &str) -> String {
    normalized(text)
        .chars()
        .filter(|char| !is_invisible(*char))
        .map(|char| confusable(char).unwrap_or(char))
        .collect()
}

fn scripts(text: &str) -> HashSet<String> {
    let mut found = HashSet::new();
    for char in nfkc(text).chars() {
        if !is_letter(get_general_category(char)) {
            continue;
        }
        let Some(name) = unicode_name(char) else {
            found.insert("OTHER".to_string());
            continue;
        };
        if name.starts_with("CJK") || name.starts_with("IDEOGRAPHIC") {
            found.insert("HAN".to_string());
        } else {
            let script = match name.split_once(' ') {
                Some((first, _)) => first,
                None => &name,
            };
            found.insert(script.to_string());
        }
    }
    found
}

fn text_vector(text: &str) -> Vec<f64> {
    let length = text.chars().count();
    let denominator = length.max(1) as f64;
    let scripts = scripts(text);
    let normalized_text = normalized(text);
    let nfkc_text = nfkc(text);
    let skeleton_text = skeleton(text);

    let mut nonascii = 0usize;
    let mut invisible = 0usize;
    let mut combining = 0usize;
    let mut digit = 0usize;
    let mut punctuation = 0usize;
    let mut whitespace = 0usize;
    let mut currency = false;
    for char in text.chars() {
        let category = get_general_category(char);
        if !char.is_ascii() {
            nonascii += 1;
        }
        if is_invisible(char) {
            invisible += 1;
        }
        if is_combining(category) {
            combining += 1;
        }
        if is_digit(char, category) {
            digit += 1;
        }
        if is_punctuation(category) {
            punctuation += 1;
        }
        if python_isspace(char) {
            whitespace += 1;
        }
        if category == GeneralCategory::CurrencySymbol {
            currency = true;
        }
    }

    vec![
        (length.min(4096) as f64).ln_1p(),
        nonascii as f64 / denominator,
        invisible as f64 / denominator,
        combining as f64 / denominator,
        digit as f64 / denominator,
        punctuation as f64 / denominator,
        whitespace as f64 / denominator,
        if scripts.len() > 1 { 1.0 } else { 0.0 },
        scripts.len().min(8) as f64,
        if nfkc_text != text { 1.0 } else { 0.0 },
        if skeleton_text != normalized_text {
            1.0
        } else {
            0.0
        },
        if URL.is_match(&skeleton_text) {
            1.0
        } else {
            0.0
        },
        if PROMO.is_match(&skeleton_text) {
            1.0
        } else {
            0.0
        },
        if CONTACT.is_match(&normalized_text) {
            1.0
        } else {
            0.0
        },
        if currency { 1.0 } else { 0.0 },
        if nfkc_text.contains('%') { 1.0 } else { 0.0 },
        text.chars().filter(|char| *char == '!').count().min(16) as f64,
    ]
}

/// `_number` of the reference: finite, non-negative floats only. Boolean provenance
/// flags arrive as already-scaled `0.0`/`1.0` values from [`SpamContext`].
fn number(value: Option<f64>) -> Option<f64> {
    value.filter(|number| number.is_finite() && *number >= 0.0)
}

/// Return bounded/interpretable floats, never labels or raw identity fields.
///
/// Counts and time gaps are capped then log1p transformed. Fractions are clipped
/// to [0,1]. Every numeric input has a separate missing bit; unknown is not zero.
fn vectorize(record: &SpamRecord) -> Vec<f64> {
    let name = &record.name;
    let symbol = &record.symbol;
    let normal_symbol = casefold(python_strip(symbol));
    let symbol_key = skeleton(symbol);
    let name_key = skeleton(name);

    let mut values = text_vector(name);
    values.extend(text_vector(symbol));
    values.push(if CANONICAL_SYMBOLS.contains(&normal_symbol.as_str()) {
        1.0
    } else {
        0.0
    });
    values.push(
        if CANONICAL_SYMBOLS.contains(&symbol_key.as_str()) && symbol_key != normal_symbol {
            1.0
        } else {
            0.0
        },
    );
    values.push(if !name_key.is_empty() && name_key == symbol_key {
        1.0
    } else {
        0.0
    });

    let decimals = record
        .decimals
        .map(|decimals| decimals.min(255) as f64 / 255.0);
    values.push(decimals.unwrap_or(0.0));
    values.push(if decimals.is_none() { 1.0 } else { 0.0 });

    for (key, cap) in CONTEXT {
        let number = number(record.context.get(key).copied().flatten());
        let value = number.map_or(0.0, |number| number.min(cap));
        values.push(if cap == 1.0 { value } else { value.ln_1p() });
        values.push(if number.is_none() { 1.0 } else { 0.0 });
    }
    values
}

fn feature_values(record: &SpamRecord, exclude_provenance: bool) -> Vec<f64> {
    let mut values = vectorize(record);
    if exclude_provenance {
        for (index, name) in FEATURE_NAMES.iter().enumerate() {
            if PROVENANCE_FEATURE_PREFIXES
                .iter()
                .any(|prefix| name.starts_with(prefix))
            {
                values[index] = if name.ends_with("_missing") { 1.0 } else { 0.0 };
            }
        }
    }
    values
}

fn sigmoid(x: f64) -> f64 {
    1.0 / (1.0 + (-x.clamp(-700.0, 700.0)).exp())
}

/// Probability from an already-computed logit, applying the exported calibration.
fn probability_from_logit(model: &SpamModel, logit: f64) -> f64 {
    sigmoid(model.calibration.slope * logit + model.calibration.intercept)
}

fn validate_model(model: &SpamModel) -> Result<(), String> {
    if model.format_version != 1 || model.features != *FEATURE_NAMES {
        return Err("Packaged spam model does not match this rotki version".to_string());
    }

    let input_count = FEATURE_NAMES.len();
    let hidden_count = model.w1.len();
    if model.mean.len() != input_count
        || model.scale.len() != input_count
        || model.reference.len() != input_count
        || model.b1.len() != hidden_count
        || model.w2.len() != hidden_count
        || model.w1.iter().any(|row| row.len() != input_count)
    {
        return Err("Packaged spam model has inconsistent parameters".to_string());
    }
    Ok(())
}

/// The immutable embedded model, parsed and validated once per process.
static MODEL: LazyLock<SpamModel> = LazyLock::new(|| {
    let model: SpamModel =
        serde_json::from_str(SPAM_MODEL_JSON).expect("packaged spam model is not valid JSON");
    validate_model(&model).unwrap_or_else(|error| panic!("{error}"));
    model
});

/// Access the validated immutable embedded model.
fn load_spam_model() -> &'static SpamModel {
    &MODEL
}

/// Return the model's advisory estimate for one token's bounded metadata.
pub(crate) fn predict_spam(record: &SpamRecord) -> SpamPrediction {
    let model = load_spam_model();
    let values = feature_values(record, model.exclude_provenance);
    let x: Vec<f64> = values
        .iter()
        .zip(&model.mean)
        .zip(&model.scale)
        .map(|((value, mean), scale)| (value - mean) / scale)
        .collect();
    let mut pre_activation = Vec::with_capacity(model.w1.len());
    let mut hidden = Vec::with_capacity(model.w1.len());
    for (row, bias) in model.w1.iter().zip(&model.b1) {
        let mut dot = 0.0;
        for (weight, item) in row.iter().zip(&x) {
            dot += weight * item;
        }
        let pre = dot + bias;
        pre_activation.push(pre);
        hidden.push(pre.max(0.0));
    }
    let mut base_logit = model.b2;
    for (activation, weight) in hidden.iter().zip(&model.w2) {
        base_logit += activation * weight;
    }
    let probability = probability_from_logit(model, base_logit);

    // One-at-a-time replacement with training medians. This is local sensitivity, not
    // a causal explanation or an additive decomposition of the probability. Only the
    // single perturbed input coordinate and its contribution to each hidden unit are
    // recomputed, which is algebraically identical to a full forward pass.
    let mut impacts = Vec::new();
    for (index, name) in FEATURE_NAMES.iter().enumerate() {
        let reference = (model.reference[index] - model.mean[index]) / model.scale[index];
        let delta_x = reference - x[index];
        if delta_x == 0.0 {
            continue;
        }
        let mut delta_logit = 0.0;
        for (unit, row) in model.w1.iter().enumerate() {
            let ablated = (pre_activation[unit] + row[index] * delta_x).max(0.0);
            delta_logit += (ablated - hidden[unit]) * model.w2[unit];
        }
        let ablated_probability = probability_from_logit(model, base_logit + delta_logit);
        let delta = probability - ablated_probability;
        if delta > 0.001 {
            impacts.push(SpamModelReason {
                feature: name.clone(),
                value: values[index],
                probability_delta: delta,
            });
        }
    }
    impacts.sort_by(|left, right| {
        right
            .probability_delta
            .partial_cmp(&left.probability_delta)
            .expect("model probabilities are never NaN")
    });
    impacts.truncate(5);

    SpamPrediction {
        spam_probability: probability,
        flagged: probability >= model.threshold,
        threshold: model.threshold,
        observed_signals: evidence(record),
        model_reasons: impacts,
    }
}

/// Describe observed metadata without claiming a spam verdict/authenticity.
fn evidence(record: &SpamRecord) -> Vec<SpamSignal> {
    use SpamSignalCode as Code;
    use SpamSignalField as Field;

    let mut facts = Vec::new();
    for (field, text) in [
        (Field::Name, record.name.as_str()),
        (Field::Symbol, record.symbol.as_str()),
    ] {
        let mut push = |code| facts.push(SpamSignal::new(field, code));
        if !text.is_ascii() {
            push(Code::NonAscii);
        }
        if text.chars().any(is_invisible) {
            push(Code::InvisibleCharacters);
        }
        if text
            .chars()
            .any(|char| is_combining(get_general_category(char)))
        {
            push(Code::CombiningMarks);
        }
        if scripts(text).len() > 1 {
            push(Code::MixedScripts);
        }
        let text_key = skeleton(text);
        if URL.is_match(&text_key) {
            push(Code::Url);
        }
        if PROMO.is_match(&text_key) {
            push(Code::Promotion);
        }
    }

    let symbol = &record.symbol;
    if CANONICAL_SYMBOLS.contains(&casefold(python_strip(symbol)).as_str()) {
        facts.push(SpamSignal::new(Field::Symbol, Code::CommonSymbol));
    } else if CANONICAL_SYMBOLS.contains(&skeleton(symbol).as_str()) {
        facts.push(SpamSignal::new(Field::Symbol, Code::LookalikeSymbol));
    }

    let context_value = |key: &str| number(record.context.get(key).copied().flatten());
    if context_value("known_origin_fraction").is_none() {
        facts.push(SpamSignal::new(
            Field::Context,
            Code::KnownOriginUnavailable,
        ));
    }

    for (key, code) in [
        ("max_token_transfer_count", Code::MaxTokenTransfers),
        ("mean_token_transfer_count", Code::MeanTokenTransfers),
    ] {
        if let Some(value) = context_value(key) {
            facts.push(SpamSignal {
                field: Field::Context,
                code,
                value: Some(value),
            });
        }
    }

    for (key, present, absent) in [
        (
            "in_packaged_globaldb",
            Code::InPackagedGlobaldb,
            Code::NotInPackagedGlobaldb,
        ),
        ("in_collection", Code::InCollection, Code::NotInCollection),
    ] {
        if let Some(value) = context_value(key) {
            let code = if value != 0.0 { present } else { absent };
            facts.push(SpamSignal::new(Field::Context, code));
        }
    }

    facts
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use serde::Deserialize;

    use super::*;

    const FIXTURES: &str = include_str!("../tests/fixtures/spam_detection_parity.json");

    #[derive(Deserialize)]
    struct FixtureFile {
        feature_names: Vec<String>,
        cases: Vec<FixtureCase>,
        skeletons: Vec<SkeletonCase>,
    }

    #[derive(Deserialize)]
    struct FixtureCase {
        label: String,
        record: FixtureRecord,
        skeleton: SkeletonPair,
        vector: Vec<f64>,
        feature_values: Vec<f64>,
        evidence: Vec<SpamSignal>,
        prediction: FixturePrediction,
    }

    #[derive(Deserialize)]
    struct FixtureRecord {
        name: Option<String>,
        symbol: Option<String>,
        decimals: Option<u32>,
        context: HashMap<String, serde_json::Value>,
    }

    impl FixtureRecord {
        fn into_record(self) -> SpamRecord {
            SpamRecord {
                name: self.name.unwrap_or_default(),
                symbol: self.symbol.unwrap_or_default(),
                decimals: self.decimals,
                context: self
                    .context
                    .into_iter()
                    .map(|(key, value)| {
                        let value = match value {
                            serde_json::Value::Null => None,
                            serde_json::Value::Bool(flag) => Some(if flag { 1.0 } else { 0.0 }),
                            serde_json::Value::Number(number) => number.as_f64(),
                            other => panic!("unsupported context fixture value {other:?}"),
                        };
                        (key, value)
                    })
                    .collect(),
            }
        }
    }

    #[derive(Deserialize)]
    struct SkeletonPair {
        name: String,
        symbol: String,
    }

    #[derive(Deserialize)]
    struct FixturePrediction {
        spam_probability: f64,
        flagged: bool,
        threshold: f64,
        observed_signals: Vec<SpamSignal>,
        model_reasons: Vec<FixtureReason>,
    }

    #[derive(Deserialize)]
    struct FixtureReason {
        feature: String,
        value: f64,
        probability_delta: f64,
    }

    #[derive(Deserialize)]
    struct SkeletonCase {
        input: String,
        expected: String,
    }

    fn fixtures() -> FixtureFile {
        serde_json::from_str(FIXTURES).expect("parity fixtures are valid JSON")
    }

    fn assert_values_close(actual: &[f64], expected: &[f64], tolerance: f64, label: &str) {
        assert_eq!(actual.len(), expected.len(), "{label}: length");
        for (index, (actual, expected)) in actual.iter().zip(expected).enumerate() {
            assert!(
                (actual - expected).abs() <= tolerance,
                "{label}[{index}]: {actual} != {expected}",
            );
        }
    }

    fn assert_probability_close(actual: f64, expected: f64, label: &str) {
        assert!(
            (actual - expected).abs() <= 1e-12 * expected.abs().max(1e-12),
            "{label}: probability {actual} != {expected}",
        );
    }

    #[test]
    fn model_matches_this_port() {
        let model = load_spam_model();
        assert_eq!(model.format_version, 1);
        assert_eq!(model.features, *FEATURE_NAMES);
        assert_eq!(FEATURE_NAMES.len(), 59);
        assert_eq!(model.w1.len(), 16);
        assert!(model.w1.iter().all(|row| row.len() == 59));
        assert_eq!(model.threshold, 0.8708363650723653);
        assert!(model.exclude_provenance);
    }

    #[test]
    fn feature_names_match_python() {
        let fixtures = fixtures();
        assert_eq!(*FEATURE_NAMES, fixtures.feature_names);
    }

    #[test]
    fn vectors_evidence_and_predictions_match_python() {
        for case in fixtures().cases {
            let label = &case.label;
            let record = case.record.into_record();
            assert_eq!(
                skeleton(&record.name),
                case.skeleton.name,
                "{label}: name skeleton"
            );
            assert_eq!(
                skeleton(&record.symbol),
                case.skeleton.symbol,
                "{label}: symbol skeleton",
            );
            assert_values_close(&vectorize(&record), &case.vector, 1e-12, label);
            assert_values_close(
                &feature_values(&record, true),
                &case.feature_values,
                1e-12,
                label,
            );
            assert_eq!(evidence(&record), case.evidence, "{label}: evidence");

            let prediction = predict_spam(&record);
            assert_probability_close(
                prediction.spam_probability,
                case.prediction.spam_probability,
                label,
            );
            assert_eq!(
                prediction.flagged, case.prediction.flagged,
                "{label}: flagged"
            );
            assert_eq!(
                prediction.threshold, case.prediction.threshold,
                "{label}: threshold",
            );
            assert_eq!(
                prediction.observed_signals, case.prediction.observed_signals,
                "{label}: observed signals",
            );
            assert_eq!(
                prediction.model_reasons.len(),
                case.prediction.model_reasons.len(),
                "{label}: reason count",
            );
            for (actual, expected) in prediction
                .model_reasons
                .iter()
                .zip(&case.prediction.model_reasons)
            {
                assert_eq!(actual.feature, expected.feature, "{label}: reason feature");
                assert!(
                    (actual.value - expected.value).abs() <= 1e-12,
                    "{label}: reason value {} != {}",
                    actual.value,
                    expected.value,
                );
                assert!(
                    (actual.probability_delta - expected.probability_delta).abs() <= 1e-9,
                    "{label}: reason delta {} != {}",
                    actual.probability_delta,
                    expected.probability_delta,
                );
            }
        }
    }

    #[test]
    fn skeleton_matches_python_case_folding() {
        for case in fixtures().skeletons {
            assert_eq!(skeleton(&case.input), case.expected, "{}", case.input);
        }
    }

    #[test]
    fn missing_context_is_missing_not_zero() {
        let record = SpamRecord {
            name: "Sample".to_string(),
            symbol: "SAMPLE".to_string(),
            decimals: Some(18),
            context: HashMap::new(),
        };
        let values = vectorize(&record);
        for index in (39..59).step_by(2) {
            assert_eq!(values[index], 0.0);
            assert_eq!(values[index + 1], 1.0);
        }
        assert_eq!(
            &feature_values(&record, true)[55..59],
            &[0.0, 1.0, 0.0, 1.0],
        );

        let zero_context = SpamRecord {
            context: CONTEXT
                .iter()
                .map(|(key, _)| ((*key).to_string(), Some(0.0)))
                .collect(),
            ..record.clone()
        };
        assert_ne!(
            predict_spam(&record).spam_probability,
            predict_spam(&zero_context).spam_probability,
        );
        assert!(evidence(&record).contains(&SpamSignal::new(
            SpamSignalField::Context,
            SpamSignalCode::KnownOriginUnavailable
        )));
    }

    #[test]
    fn numeric_context_is_bounded_and_rejects_invalid_values() {
        let mut context: SpamContext = CONTEXT
            .iter()
            .map(|(key, _)| ((*key).to_string(), Some(1e30)))
            .collect();
        context.insert("tx_count".to_string(), Some(f64::NAN));
        context.insert("mean_log_count".to_string(), Some(-1.0));
        context.insert("in_collection".to_string(), Some(0.0));
        let values = vectorize(&SpamRecord {
            name: "Cap".to_string(),
            symbol: "CAP".to_string(),
            decimals: None,
            context,
        });
        // tx_count missing, then max_log_count log1p(1e6) capped.
        assert_eq!(values[39], 0.0);
        assert_eq!(values[40], 1.0);
        assert_eq!(values[41], 0.0);
        assert_eq!(values[42], 1.0);
        assert_eq!(values[43], (1_000_000.0_f64).ln_1p());
        assert_eq!(values[44], 0.0);
        assert_eq!(values[49], (315_576_000.0_f64).ln_1p());
        // Provenance values are excluded and marked missing by this model.
        let excluded = feature_values(
            &SpamRecord {
                context: CONTEXT
                    .iter()
                    .map(|(key, _)| ((*key).to_string(), Some(1.0)))
                    .collect(),
                ..Default::default()
            },
            true,
        );
        assert_eq!(&excluded[55..59], &[0.0, 1.0, 0.0, 1.0]);
    }

    #[test]
    fn decimals_are_scaled_and_missing_is_a_separate_feature() {
        let with_decimals = vectorize(&SpamRecord {
            name: String::new(),
            symbol: String::new(),
            decimals: Some(255),
            context: HashMap::new(),
        });
        assert_eq!(with_decimals[37], 1.0);
        assert_eq!(with_decimals[38], 0.0);

        let without_decimals = vectorize(&SpamRecord::default());
        assert_eq!(without_decimals[37], 0.0);
        assert_eq!(without_decimals[38], 1.0);
    }

    #[test]
    fn python_word_boundaries_treat_combining_marks_as_nonword() {
        assert!(PROMO.is_match("claim\u{301}"));
        assert!(CONTACT.is_match("qq\u{301}"));
        assert!(URL.is_match("foo.com\u{301}"));
        assert!(!URL.is_match("-.com"));
        assert!(URL.is_match("中-foo.com"));
    }
}
