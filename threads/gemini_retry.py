import os
import time


DEFAULT_GEMINI_MODEL_CHAIN = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
]

RETRYABLE_ERROR_MARKERS = [
    "429",
    "503",
    "10054",
    "connection reset",
    "deadline",
    "high demand",
    "internal",
    "overloaded",
    "quota",
    "rate limit",
    "resource exhausted",
    "temporarily unavailable",
    "timeout",
    "timed out",
    "unavailable",
]

FALLBACK_ERROR_MARKERS = RETRYABLE_ERROR_MARKERS + [
    "404",
    "not found",
    "not supported",
]

AUTH_ERROR_MARKERS = [
    "403",
    "api key",
    "forbidden",
    "leaked",
    "permission denied",
    "unauthorized",
]


def get_gemini_model_chain():
    configured = os.getenv("GEMINI_MODEL_CHAIN", "").strip()
    if not configured:
        return DEFAULT_GEMINI_MODEL_CHAIN
    models = [model.strip() for model in configured.split(",") if model.strip()]
    return models or DEFAULT_GEMINI_MODEL_CHAIN


def is_auth_error(error):
    message = str(error).lower()
    return any(marker in message for marker in AUTH_ERROR_MARKERS)


def is_retryable_error(error):
    message = str(error).lower()
    return any(marker in message for marker in RETRYABLE_ERROR_MARKERS)


def should_try_next_model(error):
    message = str(error).lower()
    return any(marker in message for marker in FALLBACK_ERROR_MARKERS)


def generate_content_with_retries(
    client,
    build_request,
    model_chain=None,
    attempts_per_model=3,
    base_delay_seconds=5,
    progress_callback=None,
    log_prefix="GEMINI",
):
    models = model_chain or get_gemini_model_chain()
    last_error = None

    for model_name in models:
        for attempt in range(1, attempts_per_model + 1):
            try:
                if progress_callback:
                    progress_callback(f"{log_prefix}: calling {model_name} (attempt {attempt}/{attempts_per_model})")
                request_kwargs = build_request(model_name)
                response = client.models.generate_content(model=model_name, **request_kwargs)
                return response, model_name
            except Exception as error:
                last_error = error
                if is_auth_error(error):
                    raise

                can_retry_model = attempt < attempts_per_model and is_retryable_error(error)
                if can_retry_model:
                    wait_time = base_delay_seconds * attempt
                    if progress_callback:
                        progress_callback(
                            f"{log_prefix}: transient error on {model_name}; retrying in {wait_time}s"
                        )
                    time.sleep(wait_time)
                    continue

                if should_try_next_model(error):
                    if progress_callback:
                        progress_callback(f"{log_prefix}: switching model after {model_name} failed")
                    break

                raise

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")
