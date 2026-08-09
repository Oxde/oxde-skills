// analyze/heuristics.mjs — static analysis of a SKILL.md. Pure; treats content as untrusted data.
// Produces the labels the site shows: language, API needs, network use, promo, safety grade.

const RX = {
  frontmatterEnv: /required_environment_variables:\s*\[?\s*([^\]\n]*)/i,
  apiKey: /\bapi[\s_-]?key\b|\bbearer\s+token\b|\boauth\b|client_secret|access[\s_-]?token/i,
  signup: /sign\s?up|create (an? )?account|register (at|on)|subscription required|paid plan/i,
  network: /https?:\/\/|websocket|webhook|\bcurl\b|\bfetch\(|\bPOST\b|\bGET\s+http/i,
  payment: /x402|USDC|per[- ]call pricing|\$\d+(\.\d+)?\s*\/?\s*(mo|month|call|run|request)|crypto payment|wallet address/i,
  funnel: /t\.me\/|discord\.gg\/|referral|affiliate|utm_|join (my|our) (channel|community|newsletter)|follow (me|us) on/i,
  overrides: /ignore (all )?(previous|prior|above) (instructions|rules)|disregard (the )?system prompt|you are now|jailbreak/i,
  exfil: /(send|post|upload|forward)[^.\n]{0,60}(conversation|context|history|credentials|api[\s_-]?key|environment)/i,
  dangerousShell: /rm\s+-rf|sudo\s|chmod\s+777|curl[^|\n]{0,120}\|\s*(ba)?sh|eval\s*\(|base64\s+-d/i,
  outputDirective: /output only|no reasoning|no explanation|do not (explain|mention|reveal)/i,
  credHarvest: /(paste|enter|provide) (your|the) (api[\s_-]?key|password|secret|seed phrase|private key)/i,
  script: /```(bash|sh|python|js|javascript|typescript)|\.py\b|\.sh\b|\.mjs\b/i,
};

// Authors announce abandonment in prose, not metadata — a skill can be fresh by
// release date and still say "no longer maintained" in its first line.
const DEPRECATED = /\b(deprecat|depreciat)(ed|ion)?\b|no longer maintained|unmaintained|superseded by|use .{0,40} instead\b|archived|discontinued|已废弃|已弃用|不再维护/i;
export const isDeprecated = (text) => DEPRECATED.test(text ?? '');

const CJK = /[一-鿿㐀-䶿]/g;
const HANGUL = /[가-힯]/g;
const KANA = /[぀-ヿ]/g;
const CYRILLIC = /[Ѐ-ӿ]/g;

// Which human language is this skill written in? Matters because a Chinese-only
// SKILL.md is unusable to an English-speaking operator, and vice versa.
export function detectLanguage(text) {
  if (!text) return { code: 'unknown', label: 'Unknown' };
  const sample = text.slice(0, 8000);
  const total = sample.replace(/\s/g, '').length || 1;
  const zh = (sample.match(CJK) || []).length / total;
  const ja = (sample.match(KANA) || []).length / total;
  const ko = (sample.match(HANGUL) || []).length / total;
  const ru = (sample.match(CYRILLIC) || []).length / total;
  if (ja > 0.05) return { code: 'ja', label: '日本語' };
  if (ko > 0.05) return { code: 'ko', label: '한국어' };
  if (ru > 0.10) return { code: 'ru', label: 'Русский' };
  if (zh > 0.20) return { code: 'zh', label: '中文' };
  if (zh > 0.03) return { code: 'zh-en', label: '中文 + EN' };
  return { code: 'en', label: 'English' };
}

export function analyzeSkillMd(md) {
  if (!md) return null;
  const envMatch = md.match(RX.frontmatterEnv);
  const envVars = envMatch ? envMatch[1].split(',').map(s => s.replace(/["'\[\]]/g, '').trim()).filter(Boolean) : [];

  const flags = [];
  if (RX.overrides.test(md)) flags.push('override-attempt');
  if (RX.credHarvest.test(md)) flags.push('credential-harvest');
  if (RX.exfil.test(md)) flags.push('possible-exfil');
  if (RX.dangerousShell.test(md)) flags.push('dangerous-shell');
  if (RX.outputDirective.test(md)) flags.push('output-directive');
  const promo = RX.payment.test(md) || RX.funnel.test(md);
  if (promo) flags.push('promotion');

  const severe = flags.some(f => ['override-attempt', 'credential-harvest', 'possible-exfil', 'dangerous-shell'].includes(f));
  const grade = severe ? 'risky' : flags.length > 0 ? 'review' : 'safe';

  return {
    language: detectLanguage(md),
    deprecated: isDeprecated(md.slice(0, 2000)), // only the header region counts as an announcement
    apiNeeded: { flag: envVars.length > 0 || RX.apiKey.test(md) || RX.signup.test(md), envVars: envVars.slice(0, 6) },
    network: RX.network.test(md),
    promo,
    noCode: !RX.script.test(md),
    safety: { grade, flags },
    tokens: Math.round(md.length / 4),
  };
}

// publisher aggregation, tracking which registries each one ships on
export function buildPublishers(details, officialOrgs) {
  const official = new Set(officialOrgs.map(o => o.org.toLowerCase()));
  const map = new Map();
  for (const d of details) {
    const o = d.owner;
    if (!o?.handle) continue;
    const p = map.get(o.handle) ?? {
      handle: o.handle, displayName: o.displayName ?? o.handle, image: o.image ?? null,
      skillCount: 0, totalDownloads: 0, totalStars: 0,
      official: official.has(o.handle.toLowerCase()), registries: new Set(),
    };
    p.skillCount++;
    p.totalDownloads += d.skill?.stats?.downloads ?? 0;
    p.totalStars += d.skill?.stats?.stars ?? 0;
    p.registries.add('clawhub');
    map.set(o.handle, p);
  }
  return map;
}
