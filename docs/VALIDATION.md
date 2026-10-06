# Validation - 2026-10-06

Windows / Python 3.12 / Node 22 / pnpm 11.19.0. TypeScript checks and production builds passed locally.
All examples use synthetic data. Local tests do not imply successful hosted CI or quality on real customer data.

3 tests passed. Real faster-whisper tiny CPU invocation transcribed our synthetic Russian WAV and produced word timestamps. It misrecognized one word in the final sentence. This is one functional smoke test, not a speech recognition benchmark. Keyword checklist scoring is deterministic, not LLM evaluation. Audio generated using installed Microsoft Irina speech synthesis.

Docker image built and started locally as a non-root user. Static UI and health endpoint returned successfully. Authored demo transcript and synthetic WAV endpoints were checked.

## Selected interface verification

Final TypeScript/Vite build passed. Browser review at measured 1454 × 818 desktop and 443 px mobile width found no horizontal page overflow. Escape closes project dialogs. `preview.png` is an actual local application screenshot, not a design mockup.
Actual WAV playback and transcript seeking were checked; a speaker role was changed manually. The keyword checklist showed evidence for 3/3 checks.
