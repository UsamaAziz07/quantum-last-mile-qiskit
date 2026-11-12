# 02 — PARALLEL TASK BOARD (deadline 12 Nov 2026, 11:59pm — internal freeze 9:30pm, submit by 10:30pm)

Four submissions required: **GitHub repo · Report (.docx) incl. architecture diagram · 3-min video (Drive, "anyone with link") · Submission form** https://forms.gle/jSRrXaHkjVb7G7AK8

Rule of thumb: everything reads `01_PROJECT_SPEC.md`. Final numbers come from `results/` in the repo — **report and video must quote the repo's numbers**.

| ID | Task | Tool | Needs | Output | Time |
|----|------|------|-------|--------|------|
| T1 | Env + repo + code build | **Antigravity** (give it `ANTIGRAVITY_INSTRUCTIONS.md` + skeleton zip) | — | working repo, results/ | 0–6h |
| T2 | Architecture diagram | draw.io / Mermaid Live / Napkin AI | spec only | `docs/architecture.png` | 0–1h |
| T3 | Report draft (text) | Claude / Gemini / ChatGPT | spec + `03_REPORT_OUTLINE.md` | draft .docx with placeholders [RESULT] | 0–3h |
| T4 | Pitch script + slides/visuals | Gemini / ChatGPT + Canva/PowerPoint | spec + `04_PITCH_AND_DEMO_SCRIPT.md` | script, 4–5 slides | 0–3h |
| T5 | Learn the concepts (defense) | Claude/ChatGPT chat | `05_DEFENSE_QA.md` | everyone can answer Q&A | all day |
| T6 | Fill real numbers into report | human + AI | T1 results | final report .docx | 6–7.5h |
| T7 | Record video (≤3:00) | OBS Studio / Zoom / Loom → Google Drive | T1 demo, T4 script | video link | 7–8.5h |
| T8 | QA + submit | human | everything | form submitted | 8.5–10h |

## Task cards

### T1 — Code & GitHub (Antigravity)  ★ critical path
1. Unzip `qlogistics_skeleton.zip`, open the folder in Antigravity.
2. First prompt: *"Read AGENTS.md and 01_PROJECT_SPEC.md fully, then execute the build order in AGENTS.md step by step. Commit after each step. Stop and show me the HANDOFF block when done."*
3. Create an empty PUBLIC GitHub repo yourself, sign in to git in Antigravity, give it the URL.
4. Checkpoints (ask for status): ① env imports work (~30 min) ② classical optimum printed ③ QUBO matches optimum ④ QAOA runs ⑤ results/ + README ⑥ pushed + fresh-clone test.
5. **Limit-saving tips:** don't ask it to "improve everything"; one build-order step per message; paste error messages instead of re-explaining; if Antigravity quota runs out, continue in Claude/Gemini by pasting `00_HANDOFF_SUMMARY.md` + the failing file.
Done when: `python -m src.run_demo` works from a clean clone, `pytest` passes, results/ committed.

### T2 — Architecture diagram
Paste the Mermaid block from the spec into mermaid.live (or recreate in draw.io), export PNG (high-res), save as `docs/architecture.png`. Label colours: blue = classical, purple = quantum. Give to T1 (README) and T3 (report).

### T3 — Report draft
Paste `01_PROJECT_SPEC.md` + `03_REPORT_OUTLINE.md` to the AI, ask for a ~6–8 page Word report with `[RESULT: ...]` placeholders. Keep "Limitations" honest and specific. Export .docx.

### T4 — Pitch script
Use `04_PITCH_AND_DEMO_SCRIPT.md` as the template. Make 4–5 slides (problem, formulation, architecture, results, limits). Rehearse with a timer: must be **≤ 3:00**.

### T5 — Concept study
Chat with any AI: "Explain QAOA / QUBO / Ising / slack variables to a beginner using the delivery example." Then quiz yourselves with `05_DEFENSE_QA.md`. Assign each teammate 2–3 questions.

### T6 — Finalise report
After T1 hands off numbers: replace every placeholder; paste figures from `results/`; include architecture diagram; add repo link; check numbers match `results/summary.json`.

### T7 — Video
Screen-record: slides (≈1:15) → terminal running `python -m src.run_demo` (≈1:00, speed up/trim if slow, or show pre-recorded output) → results plot + limitations (≈0:45). Upload to Google Drive → Share → "Anyone with the link". **Open the link in an incognito window to test.**

### T8 — QA & submit (checklist)
- [ ] Repo is public; fresh clone + README steps work; last commit before the deadline
- [ ] Report .docx contains diagram, results, baseline comparison, limitations, repo link
- [ ] Video ≤ 3:00, link opens incognito
- [ ] README credits Qiskit docs + states AI assistants used
- [ ] Form submitted; screenshot the confirmation

## Timeline (assuming start ≈ 2pm)
2:00 setup/T1 start · 3:00 T2 done · 5:00 T3/T4 drafts · 8:00 T1 code complete (target earlier) · 9:00 report final · 10:00 video uploaded · 10:30 SUBMIT · 11:59 absolute cutoff.
**Cut-scope plan if behind:** drop optional items (scaling, noise, SA); keep QAOA p=1..2, brute-force baseline, greedy, plots, README.
