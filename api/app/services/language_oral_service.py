"""Language Oral Practice service — French STT + 4-dimension async grading."""

import asyncio
import json
import logging
import re
import tempfile
from typing import Optional

import google.generativeai as genai

from app.config import get_settings
from app.models.language_oral_schemas import (
    OralDimensionEvidence,
    OralDimensionScore,
    OralGrading,
)

logger = logging.getLogger(__name__)

# Valid JSON escape characters after backslash
_VALID_JSON_ESCAPES = set('"\\/bfnrtu')

# Dimension weights for oral French grading
DIMENSION_WEIGHTS = {
    "grammar": 2.0,
    "lexical": 1.5,
    "discourse": 1.5,
    "task": 1.0,
}


def _fix_json_escapes(s: str) -> str:
    """Fix invalid backslash escapes in Gemini JSON output."""
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            next_char = s[i + 1]
            if next_char in _VALID_JSON_ESCAPES:
                result.append(s[i])
                result.append(next_char)
                i += 2
            else:
                result.append('\\\\')
                result.append(next_char)
                i += 2
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def _mime_to_extension(mime_type: str) -> str:
    """Map MIME type to file extension."""
    mapping = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/m4a": ".m4a",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
    }
    return mapping.get(mime_type, ".webm")


class LanguageOralService:
    """Handles French audio transcription and oral monologue grading."""

    def __init__(self):
        settings = get_settings()
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
            self.configured = True
        else:
            self.model = None
            self.configured = False

    # ==================== Transcription ====================

    async def transcribe_french(self, audio_bytes: bytes, mime_type: str) -> str:
        """Transcribe French audio via Cloud STT (Chirp 2), Gemini fallback."""

        def _run_stt():
            import subprocess
            import uuid
            from google.cloud import storage
            from google.cloud.speech_v2 import SpeechClient
            from google.cloud.speech_v2.types import cloud_speech

            project_id = "leetloop-485404"
            location = "us-central1"
            bucket_name = get_settings().gcs_audio_bucket
            if not bucket_name:
                raise RuntimeError("GCS bucket not configured (gcs_audio_bucket)")

            # Chirp 2 natively supports WebM/Opus and OGG/Opus.
            stt_supported = {"audio/webm", "audio/ogg"}
            if mime_type not in stt_supported:
                suffix = _mime_to_extension(mime_type)
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
                    tmp_in.write(audio_bytes)
                    tmp_in_path = tmp_in.name
                tmp_out_path = tmp_in_path + ".ogg"
                try:
                    result = subprocess.run(
                        ["ffmpeg", "-i", tmp_in_path, "-c:a", "libopus", "-b:a", "32k",
                         "-ar", "16000", "-ac", "1", tmp_out_path, "-y"],
                        capture_output=True, timeout=60,
                    )
                    if result.returncode != 0:
                        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr[:200]}")
                    with open(tmp_out_path, "rb") as f:
                        audio_data = f.read()
                    upload_mime = "audio/ogg"
                    upload_ext = "ogg"
                finally:
                    import os
                    os.unlink(tmp_in_path)
                    if os.path.exists(tmp_out_path):
                        os.unlink(tmp_out_path)
            else:
                audio_data = audio_bytes
                upload_mime = mime_type
                upload_ext = "webm" if "webm" in mime_type else "ogg"

            # Upload to GCS temp
            blob_path = f"stt-temp/{uuid.uuid4()}.{upload_ext}"
            gcs_client = storage.Client()
            bucket = gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(audio_data, content_type=upload_mime)
            gcs_uri = f"gs://{bucket_name}/{blob_path}"

            try:
                client = SpeechClient(
                    client_options={"api_endpoint": f"{location}-speech.googleapis.com"}
                )

                config = cloud_speech.RecognitionConfig(
                    auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                    language_codes=["fr-FR"],
                    model="chirp_2",
                    features=cloud_speech.RecognitionFeatures(
                        enable_automatic_punctuation=True,
                    ),
                )

                request = cloud_speech.BatchRecognizeRequest(
                    recognizer=f"projects/{project_id}/locations/{location}/recognizers/_",
                    config=config,
                    files=[
                        cloud_speech.BatchRecognizeFileMetadata(uri=gcs_uri),
                    ],
                    recognition_output_config=cloud_speech.RecognitionOutputConfig(
                        inline_response_config=cloud_speech.InlineOutputConfig(),
                    ),
                )

                operation = client.batch_recognize(request=request)
                response = operation.result(timeout=300)

                transcript_parts = []
                for file_result in response.results.values():
                    for result in file_result.transcript.results:
                        if result.alternatives:
                            transcript_parts.append(result.alternatives[0].transcript)

                return " ".join(transcript_parts).strip()
            finally:
                try:
                    blob.delete()
                except Exception:
                    pass

        try:
            transcript = await asyncio.to_thread(_run_stt)
            if not transcript:
                logger.warning("French STT returned empty, falling back to Gemini")
                return await self._transcribe_french_gemini_fallback(audio_bytes, mime_type)
            return transcript
        except Exception as e:
            logger.warning("French STT failed (%s), falling back to Gemini", e)
            return await self._transcribe_french_gemini_fallback(audio_bytes, mime_type)

    async def _transcribe_french_gemini_fallback(self, audio_bytes: bytes, mime_type: str) -> str:
        """Fallback: Gemini-based French transcription."""
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        prompt = (
            "Transcris cet audio mot à mot. Inclus les hésitations (euh, hmm). "
            "Pas de commentaire, pas de formatage — juste la transcription brute."
        )

        suffix = _mime_to_extension(mime_type)
        uploaded_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            uploaded_file = await asyncio.to_thread(
                genai.upload_file, tmp_path, mime_type=mime_type
            )

            response = await asyncio.to_thread(
                self.model.generate_content, [prompt, uploaded_file]
            )

            return response.text.strip()
        finally:
            import os
            if uploaded_file:
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # ==================== Grading ====================

    async def grade_monologue(
        self,
        transcript: str,
        prompt_text: str,
        grammar_targets: list[str],
        vocab_targets: list[str],
        chapter_context: str = "",
    ) -> OralGrading:
        """Grade a French monologue transcript on 4 CEFR-aligned dimensions."""
        if not self.configured:
            raise RuntimeError("Gemini API key not configured")

        grading_prompt = self._build_grading_prompt(
            transcript, prompt_text, grammar_targets, vocab_targets, chapter_context
        )

        response = await asyncio.to_thread(self.model.generate_content, grading_prompt)
        return self._parse_grading_response(response.text, transcript)

    def _build_grading_prompt(
        self,
        transcript: str,
        prompt_text: str,
        grammar_targets: list[str],
        vocab_targets: list[str],
        chapter_context: str,
    ) -> str:
        grammar_note = ", ".join(grammar_targets) if grammar_targets else "grammaire générale"
        vocab_note = ", ".join(vocab_targets) if vocab_targets else "vocabulaire général"

        return f"""Tu es un examinateur DALF C1 strict mais juste. Évalue cette réponse orale d'un étudiant de français niveau B2 qui vise le C1.

CONSIGNE DONNÉE À L'ÉTUDIANT :
{prompt_text}

CIBLES GRAMMATICALES DU CHAPITRE : {grammar_note}
VOCABULAIRE ATTENDU : {vocab_note}
{f"CONTEXTE DU CHAPITRE : {chapter_context}" if chapter_context else ""}

TRANSCRIPTION DE L'ÉTUDIANT :
{transcript}

---

Évalue sur 4 dimensions (score 1-10 chacune) :

**1. GRAMMAR (Précision grammaticale)** — poids 2.0
Conjugaison, accords, temps, syntaxe, structures appropriées au registre.
- 1-3 : Erreurs systématiques qui gênent la compréhension
- 4-5 : Erreurs fréquentes mais message communiqué ; évite les structures complexes
- 6-7 : Bon contrôle des structures courantes ; erreurs dans les complexes (subjonctif, conditionnel passé)
- 8-9 : Précision constante ; structures complexes avec quelques glissements
- 10 : Quasi-natif ; usage confiant du subjonctif, concordance des temps, registres

**2. LEXICAL (Étendue lexicale)** — poids 1.5
Richesse du vocabulaire, précision, expressions idiomatiques, absence d'anglicismes.
- 1-3 : Vocabulaire très limité ; anglicismes fréquents
- 4-5 : Adéquat mais répétitif ; choix de mots imprécis
- 6-7 : Bonne étendue ; quelques expressions idiomatiques
- 8-9 : Riche ; utilise la nuance, synonymes, collocations naturelles
- 10 : Précision lexicale quasi-native ; vocabulaire abstrait ; expressions figées naturelles

**3. DISCOURSE (Discours et cohérence)** — poids 1.5
Structure logique, marqueurs de cohésion, argumentation, développement du sujet.
- 1-3 : Fragments décousus ; pas de connecteurs
- 4-5 : Connecteurs basiques (et, mais, parce que) ; flux logique minimal
- 6-7 : Connecteurs variés (donc, alors, cependant) ; progression claire
- 8-9 : Marqueurs sophistiqués (en revanche, d'ailleurs, néanmoins) ; argumentation structurée
- 10 : Discours fluide ; maîtrise de la concession, nuance, reformulation

**4. TASK (Réalisation de la tâche)** — poids 1.0
Le monologue a-t-il traité la consigne ? Profondeur d'engagement avec le thème.
- 1-3 : Traite à peine la consigne ; très court ou hors sujet
- 4-5 : Traitement partiel ; niveau superficiel
- 6-7 : Couvre les aspects principaux ; profondeur adéquate
- 8-9 : Traitement approfondi ; engage avec les nuances de la consigne
- 10 : Complet ; perspective originale ; dépasse le minimum

RÈGLES :
1. CITE DES PREUVES. Pour chaque dimension, cite 1-2 phrases exactes (5+ mots) de la transcription.
2. DIFFÉRENCIE LES SCORES. Tous les scores ne doivent PAS être dans un écart de 1 point.
3. C'EST DE L'ORAL. Attends-toi à des hésitations — pénalise les schémas, pas les « euh » individuels.
4. CIBLE C1. Évalue selon les descripteurs CEFR C1, pas la perfection native.
5. Vérifie si les CIBLES GRAMMATICALES et le VOCABULAIRE ATTENDU ont été utilisés.

Format ta réponse EXACTEMENT en JSON :
{{
  "grammar": {{
    "score": 7,
    "evidence": [{{"quote": "phrase exacte de la transcription", "analysis": "pourquoi ce score"}}],
    "summary": "résumé en une phrase"
  }},
  "lexical": {{
    "score": 6,
    "evidence": [{{"quote": "...", "analysis": "..."}}],
    "summary": "..."
  }},
  "discourse": {{
    "score": 7,
    "evidence": [{{"quote": "...", "analysis": "..."}}],
    "summary": "..."
  }},
  "task": {{
    "score": 8,
    "evidence": [{{"quote": "...", "analysis": "..."}}],
    "summary": "..."
  }},
  "feedback": "2-3 phrases de retour actionnable en français",
  "strongest_moment": "la meilleure citation de la transcription",
  "weakest_moment": "la plus grande lacune décrite"
}}

Évalue maintenant :"""

    def _parse_grading_response(self, response_text: str, transcript: str) -> OralGrading:
        """Parse Gemini's grading JSON into OralGrading."""
        # Extract JSON from response
        match = re.search(r"\{[\s\S]*\}", response_text)
        if not match:
            logger.error("No JSON found in grading response")
            return self._fallback_grading(transcript)

        json_text = _fix_json_escapes(match.group(0))
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse grading JSON: %s", e)
            return self._fallback_grading(transcript)

        scores = {}
        for dim_name in ["grammar", "lexical", "discourse", "task"]:
            dim_data = data.get(dim_name, {})
            if isinstance(dim_data, dict):
                evidence = []
                for ev in dim_data.get("evidence", []):
                    if isinstance(ev, dict):
                        evidence.append(OralDimensionEvidence(
                            quote=ev.get("quote", ""),
                            analysis=ev.get("analysis", ""),
                        ))
                scores[dim_name] = OralDimensionScore(
                    name=dim_name,
                    score=float(dim_data.get("score", 5)),
                    evidence=evidence,
                    summary=dim_data.get("summary", ""),
                )
            else:
                scores[dim_name] = OralDimensionScore(
                    name=dim_name,
                    score=float(dim_data) if isinstance(dim_data, (int, float)) else 5.0,
                    evidence=[],
                    summary="",
                )

        overall_score = self._compute_overall_score(scores)
        verdict = self._compute_verdict(overall_score)

        return OralGrading(
            transcript=transcript,
            scores=scores,
            overall_score=round(overall_score, 1),
            verdict=verdict,
            feedback=data.get("feedback", ""),
            strongest_moment=data.get("strongest_moment", ""),
            weakest_moment=data.get("weakest_moment", ""),
        )

    def _compute_overall_score(self, scores: dict[str, OralDimensionScore]) -> float:
        """Weighted average using DIMENSION_WEIGHTS."""
        weighted_sum = 0.0
        total_weight = 0.0
        for name, dim in scores.items():
            weight = DIMENSION_WEIGHTS.get(name, 1.0)
            weighted_sum += dim.score * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 5.0

    def _compute_verdict(self, overall_score: float) -> str:
        if overall_score >= 7:
            return "strong"
        elif overall_score >= 5:
            return "developing"
        return "needs_work"

    def _fallback_grading(self, transcript: str) -> OralGrading:
        """Fallback grading when Gemini fails."""
        word_count = len(transcript.split())
        base_score = min(5.0 + (word_count / 50), 7.0)  # More words = slightly higher base
        dim = OralDimensionScore(name="", score=base_score, evidence=[], summary="Évaluation automatique (service temporairement indisponible)")
        scores = {
            "grammar": OralDimensionScore(name="grammar", score=base_score, evidence=[], summary=dim.summary),
            "lexical": OralDimensionScore(name="lexical", score=base_score, evidence=[], summary=dim.summary),
            "discourse": OralDimensionScore(name="discourse", score=base_score, evidence=[], summary=dim.summary),
            "task": OralDimensionScore(name="task", score=base_score, evidence=[], summary=dim.summary),
        }
        return OralGrading(
            transcript=transcript,
            scores=scores,
            overall_score=round(base_score, 1),
            verdict=self._compute_verdict(base_score),
            feedback="Évaluation automatique — le service de notation est temporairement indisponible.",
            strongest_moment="",
            weakest_moment="",
        )

    # ==================== Audio Archival ====================

    async def archive_audio(
        self, audio_bytes: bytes, mime_type: str,
        user_id: str, session_id: str,
    ) -> Optional[str]:
        """Archive audio to GCS. Best-effort, non-blocking."""
        def _upload():
            from google.cloud import storage
            bucket_name = get_settings().gcs_audio_bucket
            if not bucket_name:
                return None
            ext = _mime_to_extension(mime_type).lstrip(".")
            blob_path = f"audio/{user_id}/language/{session_id}.{ext}"
            gcs_client = storage.Client()
            bucket = gcs_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(audio_bytes, content_type=mime_type)
            return f"gs://{bucket_name}/{blob_path}"

        try:
            return await asyncio.to_thread(_upload)
        except Exception as e:
            logger.warning("Failed to archive language audio: %s", e)
            return None


# Singleton
_service: Optional[LanguageOralService] = None


def get_language_oral_service() -> LanguageOralService:
    global _service
    if _service is None:
        _service = LanguageOralService()
    return _service
