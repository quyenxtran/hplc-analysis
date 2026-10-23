# Repository rules

- Every Python module, including tests, must be at most 5,000 UTF-8 bytes.
- JavaScript, HTML, and CSS files follow the same hard 5,000-byte limit.
- Keep text documentation/configuration files within the same limit. SVG demo
  assets are exempt. Do not weaken the guard to accommodate large source files.
- Split modules by responsibility; preserve the public command/API entry points.
- Run `python check_module_sizes.py` and the full unittest suite before pushing.
- Keep input data, numerical results, configurations, and audit JSON local.
  Track only code/docs and the two curated SVG demonstrations under `demo/`.
- Keep integration units explicit: input minutes/mV, primary area output µV·s.
- Preserve raw measurements. Document baseline/split/skim assumptions and keep
  reproducible edit histories. Do not label numerical regions as confirmed acids.
