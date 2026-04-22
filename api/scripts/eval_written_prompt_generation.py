#!/usr/bin/env python3
"""
Eval: grammar-targeted written prompt generation.

Gate for .claude/specs/language-written-openended-prd.md Batch 1.

For each of 10 hand-picked (chapter, grammar_targets, vocab_targets, genre, word_target)
tuples, generate an open-ended written prompt via Gemini, then have Gemini critique
whether the prompt would *force* each grammar target to appear in a well-written
response. Writes the report to .claude/specs/written-prompt-eval.md.

Target hit rate: >=80% grammar targets marked forced=true.

Usage:
    cd api
    python scripts/eval_written_prompt_generation.py
    python scripts/eval_written_prompt_generation.py --model gemini-2.0-flash
    python scripts/eval_written_prompt_generation.py --out ../.claude/specs/written-prompt-eval.md
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import google.generativeai as genai


# ============ Hand-picked target tuples ============
#
# Each tuple is a grammar-grounded task drawn from Grammaire Progressive B2:
#   chapter: chapter label
#   grammar_targets: 2-3 grammar points the response must exhibit
#   vocab_targets: 4-6 lexical items that should appear or whose role should appear
#   genre: how the response is framed (journal, essay, letter, dialogue, situational, story)
#   word_target: expected length
#
# Coverage: subjonctif, passé composé vs imparfait, conditionnel, pronoms relatifs,
# articles partitifs, gérondif, concordance des temps, accord du participe,
# discours indirect, voix passive.

TUPLES: list[dict] = [
    {
        "chapter": "Ch. 12 — Le subjonctif présent",
        "grammar_targets": [
            "subjonctif présent après expressions de doute et d'émotion",
            "conjonctions de subordination (bien que, avant que, à condition que)",
        ],
        "vocab_targets": ["néanmoins", "par ailleurs", "souligner", "envisager", "certes"],
        "genre": "opinion_essay",
        "word_target": 150,
    },
    {
        "chapter": "Ch. 7 — Passé composé et imparfait",
        "grammar_targets": [
            "passé composé pour actions ponctuelles",
            "imparfait pour description et arrière-plan",
            "accord du participe passé avec avoir",
        ],
        "vocab_targets": ["soudain", "tandis que", "jadis", "le lendemain", "à cette époque-là"],
        "genre": "story_continuation",
        "word_target": 200,
    },
    {
        "chapter": "Ch. 15 — Le conditionnel",
        "grammar_targets": [
            "conditionnel présent pour hypothèse",
            "conditionnel passé pour regret ou reproche",
            "si + imparfait / conditionnel",
        ],
        "vocab_targets": ["j'aurais préféré", "dans l'idéal", "faute de", "à ta place", "il vaudrait mieux"],
        "genre": "letter_writing",
        "word_target": 150,
    },
    {
        "chapter": "Ch. 9 — Pronoms relatifs",
        "grammar_targets": [
            "pronoms relatifs composés (auquel, duquel, lequel)",
            "dont avec complément de nom",
            "ce qui, ce que, ce dont",
        ],
        "vocab_targets": ["un phénomène", "une cause", "un enjeu", "un impact", "une conséquence"],
        "genre": "opinion_essay",
        "word_target": 150,
    },
    {
        "chapter": "Ch. 3 — Les articles",
        "grammar_targets": [
            "articles partitifs (du, de la, des)",
            "absence d'article après expressions de quantité",
            "de à la place de du / de la en phrase négative",
        ],
        "vocab_targets": ["beaucoup de", "un peu de", "manquer de", "se passer de", "avoir besoin de"],
        "genre": "journal_entry",
        "word_target": 100,
    },
    {
        "chapter": "Ch. 18 — Le gérondif et le participe présent",
        "grammar_targets": [
            "gérondif pour exprimer la simultanéité ou la manière",
            "participe présent pour cause ou caractérisation",
        ],
        "vocab_targets": ["tout en", "en effet", "de ce fait", "par conséquent", "compte tenu de"],
        "genre": "situational",
        "word_target": 150,
    },
    {
        "chapter": "Ch. 14 — La concordance des temps",
        "grammar_targets": [
            "concordance au passé (imparfait dans subordonnée)",
            "plus-que-parfait pour antériorité",
            "conditionnel pour futur dans le passé",
        ],
        "vocab_targets": ["avoir annoncé que", "savoir que", "espérer que", "la veille", "le jour suivant"],
        "genre": "story_continuation",
        "word_target": 200,
    },
    {
        "chapter": "Ch. 6 — Accord du participe passé",
        "grammar_targets": [
            "accord du participe passé avec être",
            "accord du participe passé avec avoir + COD antéposé",
            "participe passé des verbes pronominaux",
        ],
        "vocab_targets": ["les lettres que j'ai reçues", "une fois rentré", "s'être rendu compte", "elles se sont parlé", "ils se sont souvenus"],
        "genre": "journal_entry",
        "word_target": 150,
    },
    {
        "chapter": "Ch. 20 — Le discours indirect",
        "grammar_targets": [
            "transformation au discours indirect (changement de temps)",
            "transformation des marqueurs temporels (hier → la veille)",
            "verbes introducteurs (affirmer, prétendre, suggérer)",
        ],
        "vocab_targets": ["il a déclaré que", "elle a ajouté", "selon lui", "d'après elle", "il aurait précisé"],
        "genre": "dialogue",
        "word_target": 150,
    },
    {
        "chapter": "Ch. 11 — La voix passive",
        "grammar_targets": [
            "voix passive avec être + participe accordé",
            "complément d'agent introduit par par ou de",
            "alternatives à la passive (on, se faire + infinitif)",
        ],
        "vocab_targets": ["être mis en place", "être reconnu", "se voir attribuer", "un dispositif", "une mesure"],
        "genre": "opinion_essay",
        "word_target": 150,
    },
]


# ============ Prompts ============


def build_generation_prompt(t: dict) -> str:
    """Prompt that asks Gemini to write a scenario forcing the grammar targets.

    Uses a PLAN-THEN-WRITE approach with few-shot anchors for the hard cases where
    a genre alone doesn't force the grammar (relatives, gérondif, passive, accord).
    """
    targets_list = "\n".join(f'  - {g}' for g in t['grammar_targets'])
    vocab_list = ", ".join(t['vocab_targets'])
    return f"""You are an expert French teacher designing open-ended WRITTEN practice prompts for a B2 student targeting C1.

CHAPTER: {t['chapter']}
GENRE: {t['genre']}
WORD TARGET: ~{t['word_target']} mots

GRAMMAR POINTS THE RESPONSE MUST EXHIBIT:
{targets_list}

SUGGESTED VOCABULARY / EXPRESSIONS (the student may use these or idiomatic equivalents):
{vocab_list}

================ HOW TO FORCE GRAMMAR (read carefully) ================

A good prompt does not ASK for a grammar point — it engineers a situation where avoiding
that grammar point would produce an incoherent or unnatural response. Examples of engineered
forcing patterns:

- Subjonctif → require the writer to express DOUBT, EMOTION, or WISHES about future events,
  OR to use subordinating conjunctions that syntactically demand subjonctif (bien que, avant que,
  à condition que, pour que, à moins que). Frame contrast or concession.

- Passé composé + imparfait contrast → give a NARRATIVE SEED with a specific rupture event
  against a described background ("il faisait nuit, soudain un bruit m'a réveillé...").

- Conditionnel passé → demand that the writer REGRETS or REPROACHES a past action, or gives
  hindsight advice. ("Écrivez la lettre que vous auriez aimé recevoir...").

- Pronoms relatifs composés (auquel, duquel, lequel, dont, ce dont) → STRONG PRESSURE REQUIRED.
  The scenario must SET UP specific named entities that the student is asked to discuss in
  multiple dimensions, using non-trivial prepositional links. For example:
  "Parlez d'une personne à laquelle vous devez beaucoup, d'un projet dont vous êtes fier,
  et d'un sujet auquel vous avez consacré du temps." Or: "Analysez un problème DONT les causes
  sont multiples, en identifiant les facteurs AUXQUELS les décideurs doivent prêter attention
  et les aspects SUR LESQUELS un consensus est difficile." When the scenario itself seeds
  these exact prepositional constructions, the student inherits them in their response.

- Gérondif (en +ant) → STRONG PRESSURE REQUIRED. Frame the task as PROCEDURAL HOW (giving
  step-by-step instructions, describing how an outcome is achieved through actions), or as
  CONCURRENT ACTIONS ("racontez ce que vous faisiez PENDANT que..."). Role-play a coach, mentor,
  or trainer explaining PROCESS. Example: "Expliquez comment on apprend à cuisiner en
  improvisant tout en respectant les saveurs d'une région" — this pulls gérondifs directly.

- Concordance des temps → frame as REPORTING or RECOUNTING what someone told/thought/planned
  earlier ("racontez ce que votre grand-mère vous avait dit à propos de...").

- Accord du participe passé → narrative with FEMININE SUBJECTS using être ("Marie s'est levée...")
  AND with COD antéposés ("les lettres qu'elle a reçues, les livres que j'ai lus"). Prompt must
  introduce feminine/plural entities the student will refer back to.

- Discours indirect → prompt asks to REPORT someone else's speech after the fact
  ("Votre collègue vous a annoncé hier...").

- Voix passive → scenario must centre an INSTITUTIONAL AGENT or an EVENT whose agent matters
  less than the recipient ("un nouveau dispositif vient d'être adopté...", "la loi a été votée..."),
  or report actions by an authority where the passive is stylistically neutral.

- Articles partitifs / absence d'article → the scenario should involve DISCUSSING QUANTITIES,
  LACK, or NEED (consuming, needing, missing concrete resources — food, time, money, skills).

================ CRITICAL CONSTRAINTS ================

1. Do NOT name the grammar points in the scenario. Never write "utilisez le subjonctif".
2. Do NOT list the vocabulary inside the scenario.
3. The scenario must match the GENRE:
   - opinion_essay: argumentative, needs position + contrast.
   - journal_entry: personal reflection in the first person.
   - letter_writing: addressed to a specific named interlocutor.
   - dialogue: at least two distinct speakers, with reporting verbs.
   - situational: role-play where the writer responds to a given situation.
   - story_continuation: narrative with a seed the student continues.
4. Register: idiomatic B2-C1 French.
5. Answerable in roughly {t['word_target']} words.

================ PROCESS ================

Step 1 (internal): PLAN how each grammar point will be forced. For each point, decide WHICH
sentence in the expected response will carry it.
Step 2 (internal): Draft a scenario that embeds those forcing patterns.
Step 3: Output ONLY the final JSON below. Do not include your plan.

================ OUTPUT (JSON only) ================

{{
  "prompt_text": "<the final French scenario, 3-5 sentences>",
  "theme": "<2-4 word French label>",
  "why_this_forces_grammar": "<in ENGLISH, 1-2 sentences explaining which engineered element forces each grammar point — this is for eval only, not shown to the student>"
}}"""


def build_critic_prompt(t: dict, generated: dict) -> str:
    """Prompt that asks Gemini to judge whether the scenario realistically elicits each grammar target.

    Calibration: "forced = true" means the grammar point is the most NATURAL path for a
    competent B2-C1 response — avoiding it would require stilted circumlocutions. It does NOT
    mean "impossible to avoid by any paraphrase." Pedagogical prompts cannot reach that bar.
    """
    grammar_list = "\n".join(f'  - "{g}"' for g in t["grammar_targets"])
    return f"""You are an evaluator of French language practice prompts. Be fair and realistic.

A generator produced the following WRITTEN prompt for a B2 student:

SCENARIO:
\"\"\"{generated.get('prompt_text', '')}\"\"\"

GENRE: {t['genre']}
WORD TARGET: ~{t['word_target']} words
TARGET CEFR: B2 → C1

The generator claims this scenario will elicit these grammar points:
{grammar_list}

================ HOW TO JUDGE ================

Imagine a COMPETENT B2-C1 student writing an IDIOMATIC {t['word_target']}-word response. For each
grammar point, ask: "Is this grammar the MOST NATURAL PATH, such that avoiding it would require
stilted circumlocutions or sound unnaturally simple?"

- forced = true:
  * The grammar point sits on the natural path of an idiomatic response.
  * A B2-C1 writer aiming for C1-level discourse would reach for this structure.
  * Available rewrites that avoid the structure would be noticeably awkward, less precise, or
    less varied.
  * The scenario contains clear structural pressure toward this grammar (e.g., a reproach →
    conditionnel passé, a concession + doubt → subjonctif, instructions for HOW → gérondif,
    reporting someone else's words → discours indirect, naming entities with non-trivial
    prepositional links → pronoms relatifs composés, institutional actions → voix passive).
  * DO NOT require that the grammar be LITERALLY impossible to avoid. Pedagogical prompts
    cannot reach that bar. "Most natural path" is enough.

- forced = false:
  * The grammar point is incidental — equally natural alternatives exist.
  * The scenario does not create any specific pressure toward this structure.
  * A beginner could answer the prompt idiomatically without ever reaching for it.

================ EXAMPLES ================

Scenario: "Racontez un voyage marquant. Décrivez où vous étiez, ce qui se passait, et l'événement
soudain qui a changé la journée." Target: "passé composé + imparfait contrast" → forced=true
(narrative with explicit background-vs-rupture pressure).

Scenario: "Écrivez la lettre que vous auriez aimé envoyer à votre professeur de lycée."
Target: "conditionnel passé" → forced=true (regret/hindsight framing is the core task).

Scenario: "Donnez votre avis sur les réseaux sociaux." Target: "subjonctif" → forced=false
(no doubt/emotion/concession pressure — a student could write entirely in the indicatif).

Scenario: "Expliquez à un stagiaire COMMENT gérer un conflit client en respectant la hiérarchie
tout en préservant la relation." Target: "gérondif pour simultanéité ou manière" → forced=true
(procedural HOW + simultaneity — gérondif is the idiomatic tool).

================ OUTPUT ================

Return ONLY valid JSON, one entry per grammar target, keyed by the EXACT target string:
{{
  "<exact grammar target string>": {{ "forced": true|false, "rationale": "<1 sentence in English>" }},
  ...
}}"""


# ============ Helpers ============


def configure_gemini(model_name: str):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY must be set in api/.env")
        sys.exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def extract_json(text: str) -> dict | list:
    """Extract JSON object or array from a Gemini response that may wrap it in markdown."""
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    # Find first { or [
    start_obj = text.find("{")
    start_arr = text.find("[")
    candidates = [i for i in (start_obj, start_arr) if i != -1]
    if not candidates:
        raise ValueError(f"No JSON found in response: {text[:200]}")
    start = min(candidates)
    end = max(text.rfind("}"), text.rfind("]"))
    if end <= start:
        raise ValueError(f"Unbalanced JSON in response: {text[:200]}")
    return json.loads(text[start : end + 1])


JSON_GEN_CONFIG = {
    "response_mime_type": "application/json",
    "temperature": 0.7,
    "max_output_tokens": 2048,
}

CRITIC_GEN_CONFIG = {
    "response_mime_type": "application/json",
    "temperature": 0.2,
    "max_output_tokens": 2048,
}


def run_one(model, t: dict) -> dict:
    """Generate + critic for one tuple. Returns {tuple, generated, critic, hit_rate}."""
    gen_prompt = build_generation_prompt(t)
    gen_resp = model.generate_content(gen_prompt, generation_config=JSON_GEN_CONFIG)
    generated = extract_json(gen_resp.text)

    time.sleep(1.0)

    crit_prompt = build_critic_prompt(t, generated)
    crit_resp = model.generate_content(crit_prompt, generation_config=CRITIC_GEN_CONFIG)
    critic = extract_json(crit_resp.text)

    forced_count = 0
    for g in t["grammar_targets"]:
        entry = critic.get(g, {})
        if isinstance(entry, dict) and entry.get("forced") is True:
            forced_count += 1

    return {
        "tuple": t,
        "generated": generated,
        "critic": critic,
        "forced_count": forced_count,
        "total_targets": len(t["grammar_targets"]),
    }


# ============ Report ============


def render_report(results: list[dict], model_name: str) -> str:
    total_targets = sum(r["total_targets"] for r in results)
    total_forced = sum(r["forced_count"] for r in results)
    hit_rate = (total_forced / total_targets * 100) if total_targets else 0.0

    lines = [
        "# Written Prompt Generation — Eval Report",
        "",
        f"- Model: `{model_name}`",
        f"- Tuples: {len(results)}",
        f"- Grammar targets: {total_targets}",
        f"- Targets marked forced=true: {total_forced}",
        f"- **Hit rate: {hit_rate:.1f}%** (threshold: 80%)",
        f"- **Gate status: {'PASS' if hit_rate >= 80.0 else 'FAIL'}**",
        "",
        "## Per-tuple results",
        "",
    ]

    for i, r in enumerate(results, 1):
        t = r["tuple"]
        gen = r["generated"]
        crit = r["critic"]
        lines += [
            f"### {i}. {t['chapter']} ({t['genre']}, ~{t['word_target']} words)",
            "",
            f"**Grammar targets**:",
        ]
        for g in t["grammar_targets"]:
            lines.append(f"- {g}")
        lines += [
            "",
            f"**Vocab targets**: {', '.join(t['vocab_targets'])}",
            "",
            "**Generated scenario**:",
            "",
            f"> {gen.get('prompt_text', '').strip()}",
            "",
            f"**Theme**: {gen.get('theme', '?')}  ",
            f"**Why this forces grammar** (generator's own reasoning): {gen.get('why_this_forces_grammar', '?')}",
            "",
            "**Critic verdict**:",
            "",
            "| Grammar target | Forced? | Rationale |",
            "|---|---|---|",
        ]
        for g in t["grammar_targets"]:
            entry = crit.get(g, {})
            if isinstance(entry, dict):
                forced = "yes" if entry.get("forced") else "no"
                rationale = entry.get("rationale", "(missing)").replace("|", "\\|")
            else:
                forced = "?"
                rationale = "(critic did not return entry)"
            lines.append(f"| {g} | {forced} | {rationale} |")
        lines += [
            "",
            f"**Tuple hit rate**: {r['forced_count']}/{r['total_targets']}",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# ============ Main ============


def main():
    parser = argparse.ArgumentParser(description="Eval grammar-targeted prompt generation")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini model name")
    parser.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parents[2] / ".claude" / "specs" / "written-prompt-eval.md"),
        help="Report output path",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tuples (debug)")
    args = parser.parse_args()

    model = configure_gemini(args.model)
    tuples = TUPLES if args.limit is None else TUPLES[: args.limit]

    print(f"Running eval on {len(tuples)} tuples with model {args.model}...\n")

    results: list[dict] = []
    for i, t in enumerate(tuples, 1):
        print(f"[{i}/{len(tuples)}] {t['chapter']} ({t['genre']})...", end=" ", flush=True)
        try:
            r = run_one(model, t)
            results.append(r)
            print(f"{r['forced_count']}/{r['total_targets']} forced")
        except Exception as e:
            print(f"FAILED: {e}")
            results.append(
                {
                    "tuple": t,
                    "generated": {"prompt_text": f"(generation failed: {e})", "theme": "", "why_this_forces_grammar": ""},
                    "critic": {},
                    "forced_count": 0,
                    "total_targets": len(t["grammar_targets"]),
                }
            )
        time.sleep(1.5)

    report = render_report(results, args.model)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)

    total_targets = sum(r["total_targets"] for r in results)
    total_forced = sum(r["forced_count"] for r in results)
    hit_rate = (total_forced / total_targets * 100) if total_targets else 0.0
    print()
    print(f"Hit rate: {total_forced}/{total_targets} = {hit_rate:.1f}%")
    print(f"Report: {out_path}")
    print(f"Gate: {'PASS' if hit_rate >= 80.0 else 'FAIL'}")

    sys.exit(0 if hit_rate >= 80.0 else 1)


if __name__ == "__main__":
    main()
