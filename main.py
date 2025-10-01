# main.py
from flask import Flask, request, render_template_string
import math, os

app = Flask(__name__)

# -------- Realistic ranges (server-side truth) --------
RANGES = {
    "age": (13, 80),  # years
    "height_cm": (130, 230),  # cm
    "neck_val": (25, 60),  # cm
    "waist_val": (50, 200),  # cm
    "hip_val": (60, 200),  # cm
}

PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>U.S. Navy Body Fat Calculator</title>
  <style>
    :root {
      --bg: #0b0f14;
      --card: #121822;
      --muted: #9fb0c3;
      --accent: #5ac8fa;
      --ring: #2a80ff33;
      --text: #e9eef5;
      --danger: #ff6b6b;
      --ok: #2ecc71;
      --warn: #ffb020;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
      background: radial-gradient(1200px 800px at 80% -20%, #1a2332 0%, #0b0f14 60%);
      color: var(--text);
    }
    .wrap { max-width: 920px; margin: 40px auto; padding: 16px; }
    .card {
      background: linear-gradient(180deg, #121822, #0e141d);
      border: 1px solid #1f2a3a;
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 10px 30px #0006, inset 0 1px 0 #ffffff12;
    }
    h1 { margin: 0 0 8px 0; font-weight: 700; }
    p.muted { color: var(--muted); margin-top: 0; }
    .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
    .col-12 { grid-column: span 12; }
    .col-6 { grid-column: span 6; }
    .field { padding: 12px; border-radius: 12px; background: #0b111a; border: 1px solid #1b2636; }
    .label { font-size: 12px; color: var(--muted); margin-bottom: 6px; display: block; }
    input[type="number"]{
      width: 100%;
      font-size: 16px;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid #1e2a3b;
      background: #0f1622;
      color: var(--text);
      outline: none;
    }
    input[type="number"].bad { border-color: var(--danger); box-shadow: 0 0 0 3px #ff6b6b33; }
    .hint { font-size: 12px; color: #9fb0c3; margin-top: 6px; }
    .radio { margin-right: 10px; color: var(--muted); }
    .buttons { margin-top: 16px; display: flex; gap: 12px; }
    button {
      padding: 12px 16px;
      border-radius: 10px;
      border: 1px solid #24334a;
      background: #142033;
      color: var(--text);
      cursor: pointer;
      font-weight: 600;
    }
    button.primary { background: linear-gradient(180deg, #1c3454, #142441); border-color: #33527a; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .result { margin-top: 16px; padding: 16px; border-radius: 12px; background: #0e1520; }
    .err { color: var(--danger); }
    .ok { color: var(--ok); }
    @media (max-width: 800px){ .col-6 { grid-column: span 12; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>U.S. Navy Body Fat Calculator</h1>
      <p class="muted">Inputs are limited to realistic human ranges. Type normally; we’ll only clamp when you leave the box or submit.</p>

      {% if error %}
        <div class="result err"><strong>Error:</strong> {{ error }}</div>
      {% endif %}
      {% if result is not none %}
        <div class="result ok"><strong>Estimated Body Fat:</strong> {{ result }}%</div>
      {% endif %}

      <form id="calcForm" method="POST" novalidate>
        <div class="grid">
          <!-- Sex -->
          <div class="col-6 field">
            <span class="label">Sex</span>
            <label class="radio"><input type="radio" name="sex" value="male" {% if form.sex=='male' or not form.sex %}checked{% endif %}> Male</label>
            <label class="radio"><input type="radio" name="sex" value="female" {% if form.sex=='female' %}checked{% endif %}> Female</label>
          </div>

          <!-- Age -->
          <div class="col-6 field">
            <label class="label" for="age">Age (years)</label>
            <input type="number" id="age" name="age" min="{{ ranges.age[0] }}" max="{{ ranges.age[1] }}" step="1" placeholder="e.g., 25" value="{{ form.age or '' }}" inputmode="numeric">
            <div class="hint">Allowed: {{ ranges.age[0] }}–{{ ranges.age[1] }} years</div>
          </div>

          <!-- Height -->
          <div class="col-6 field">
            <label class="label" for="height_cm">Height (cm)</label>
            <input type="number" id="height_cm" name="height_cm" min="{{ ranges.height_cm[0] }}" max="{{ ranges.height_cm[1] }}" step="0.1" placeholder="e.g., 175.0" value="{{ form.height_cm or '' }}" inputmode="decimal">
            <div class="hint">Allowed: {{ ranges.height_cm[0] }}–{{ ranges.height_cm[1] }} cm</div>
          </div>

          <!-- Neck -->
          <div class="col-6 field">
            <label class="label" for="neck_val">Neck (cm)</label>
            <input type="number" id="neck_val" name="neck_val" min="{{ ranges.neck_val[0] }}" max="{{ ranges.neck_val[1] }}" step="0.1" placeholder="e.g., 38.0" value="{{ form.neck_val or '' }}" inputmode="decimal">
            <div class="hint">Allowed: {{ ranges.neck_val[0] }}–{{ ranges.neck_val[1] }} cm</div>
          </div>

          <!-- Waist -->
          <div class="col-6 field">
            <label class="label" for="waist_val">Waist (cm)</label>
            <input type="number" id="waist_val" name="waist_val" min="{{ ranges.waist_val[0] }}" max="{{ ranges.waist_val[1] }}" step="0.1" placeholder="e.g., 82.0" value="{{ form.waist_val or '' }}" inputmode="decimal">
            <div class="hint">Allowed: {{ ranges.waist_val[0] }}–{{ ranges.waist_val[1] }} cm</div>
          </div>

          <!-- Hip -->
          <div class="col-6 field">
            <label class="label" for="hip_val">Hip (cm) <span class="hint">(required for female)</span></label>
            <input type="number" id="hip_val" name="hip_val" min="{{ ranges.hip_val[0] }}" max="{{ ranges.hip_val[1] }}" step="0.1" placeholder="e.g., 95.0" value="{{ form.hip_val or '' }}" inputmode="decimal">
            <div class="hint">Allowed: {{ ranges.hip_val[0] }}–{{ ranges.hip_val[1] }} cm</div>
          </div>

          <div class="col-12 buttons">
            <button type="submit" id="submitBtn" class="primary">Calculate</button>
            <button type="button" id="resetBtn">Reset</button>
          </div>
        </div>
      </form>
    </div>
  </div>

  <script>
    // Allow only digits, one decimal point, and control keys.
    document.querySelectorAll('input[type="number"]').forEach(inp => {
      inp.addEventListener('keydown', function(e){
        const allowed = ["Backspace","Tab","ArrowLeft","ArrowRight","Delete","Enter",".","Home","End"];
        if ((e.key >= "0" && e.key <= "9") || allowed.includes(e.key)) {
          if (e.key === "." && this.value.includes(".")) e.preventDefault();
          return;
        }
        // Allow Ctrl/Cmd + A/C/V/X/Z/Y
        if ((e.ctrlKey || e.metaKey) && ["a","c","v","x","z","y"].includes(e.key.toLowerCase())) return;
        e.preventDefault();
      });
    });

    // Range validation rules:
    // - While typing: DON'T clamp. Just mark out-of-range as .bad so user can finish typing.
    // - On blur or on submit: clamp to [min, max].
    const inputs = Array.from(document.querySelectorAll('input[type="number"]'));
    const submitBtn = document.getElementById('submitBtn');
    const form = document.getElementById('calcForm');

    function isInRange(inp, v){
      const min = parseFloat(inp.min);
      const max = parseFloat(inp.max);
      return !Number.isNaN(v) && v >= min && v <= max;
    }

    function markValidity(inp){
      const raw = inp.value;
      if (raw === "") { inp.classList.remove('bad'); return; }
      const v = parseFloat(raw);
      if (Number.isNaN(v) || !isInRange(inp, v)) inp.classList.add('bad'); else inp.classList.remove('bad');
    }

    function clampValue(inp){
      if (inp.value === "") return;
      let v = parseFloat(inp.value);
      if (Number.isNaN(v)) return;
      const min = parseFloat(inp.min);
      const max = parseFloat(inp.max);
      if (v < min) v = min;
      if (v > max) v = max;
      // Respect 0.1 step by normalizing to 1 decimal when needed
      const step = inp.getAttribute('step');
      if (step && step.indexOf('.') >= 0) v = Math.round(v * 10) / 10;
      inp.value = v;
      inp.classList.remove('bad');
    }

    function updateSubmitDisabled(){
      const anyBad = inputs.some(i => i.classList.contains('bad'));
      submitBtn.disabled = anyBad;
    }

    // While typing, only mark invalid, don't clamp.
    inputs.forEach(inp => {
      inp.addEventListener('input', () => { markValidity(inp); updateSubmitDisabled(); });
      inp.addEventListener('blur', () => { clampValue(inp); markValidity(inp); updateSubmitDisabled(); });
      // Initial pass
      markValidity(inp);
    });
    updateSubmitDisabled();

    // Prevent submission if any field is currently invalid
    form.addEventListener('submit', (e) => {
      inputs.forEach(clampValue);
      inputs.forEach(markValidity);
      updateSubmitDisabled();
      if (submitBtn.disabled) e.preventDefault();
    });

    // Reset button
    document.getElementById('resetBtn').addEventListener('click', function(){
      form.reset();
      document.querySelectorAll('.result').forEach(n => n.remove());
      inputs.forEach(inp => inp.classList.remove('bad'));
      submitBtn.disabled = false;
    });
  </script>
</body>
</html>
"""


def navy_bodyfat_percent(sex, height_cm, neck_cm, waist_cm, hip_cm=None):
  height_in = height_cm / 2.54
  neck_in = neck_cm / 2.54
  waist_in = waist_cm / 2.54
  hip_in = hip_cm / 2.54 if hip_cm is not None else None

  if sex == "male":
    x = waist_in - neck_in
    if x <= 0 or height_in <= 0:
      return None, "For male, waist must be greater than neck, and height must be positive."
    bf = 86.010 * math.log10(x) - 70.041 * math.log10(height_in) + 36.76
    return round(bf, 2), None
  else:
    if hip_in is None:
      return None, "For female, hip is required."
    x = waist_in + hip_in - neck_in
    if x <= 0 or height_in <= 0:
      return None, "For female, waist + hip must be greater than neck, and height must be positive."
    bf = 163.205 * math.log10(x) - 97.684 * math.log10(height_in) - 78.387
    return round(bf, 2), None


def _in_range(name, value):
  lo, hi = RANGES[name]
  return lo <= value <= hi


@app.route("/", methods=["GET", "POST"])
def index():
  form = {
      "sex": request.form.get("sex", ""),
      "age": request.form.get("age", ""),
      "height_cm": request.form.get("height_cm", ""),
      "neck_val": request.form.get("neck_val", ""),
      "waist_val": request.form.get("waist_val", ""),
      "hip_val": request.form.get("hip_val", ""),
  }
  if request.method == "GET":
    return render_template_string(PAGE,
                                  result=None,
                                  error=None,
                                  form=form,
                                  ranges=RANGES)

  # Parse
  sex = form["sex"] if form["sex"] in ("male", "female") else "male"

  def parse_float(name):
    raw = form[name]
    if raw in ("", None):
      return None
    try:
      return float(raw)
    except ValueError:
      return None

  age = parse_float("age")
  height_cm = parse_float("height_cm")
  neck_cm = parse_float("neck_val")
  waist_cm = parse_float("waist_val")
  hip_cm = parse_float("hip_val")

  # Require presence
  if age is None:
    return render_template_string(PAGE,
                                  result=None,
                                  error="Please enter age.",
                                  form=form,
                                  ranges=RANGES)
  if height_cm is None:
    return render_template_string(PAGE,
                                  result=None,
                                  error="Please enter height in cm.",
                                  form=form,
                                  ranges=RANGES)
  if neck_cm is None:
    return render_template_string(PAGE,
                                  result=None,
                                  error="Please enter neck in cm.",
                                  form=form,
                                  ranges=RANGES)
  if waist_cm is None:
    return render_template_string(PAGE,
                                  result=None,
                                  error="Please enter waist in cm.",
                                  form=form,
                                  ranges=RANGES)
  if sex == "female" and hip_cm is None:
    return render_template_string(PAGE,
                                  result=None,
                                  error="Please enter hip in cm for female.",
                                  form=form,
                                  ranges=RANGES)

  # Range checks
  if not _in_range("age", age):
    lo, hi = RANGES["age"]
    return render_template_string(PAGE,
                                  result=None,
                                  error=f"Age must be between {lo} and {hi}.",
                                  form=form,
                                  ranges=RANGES)
  if not _in_range("height_cm", height_cm):
    lo, hi = RANGES["height_cm"]
    return render_template_string(
        PAGE,
        result=None,
        error=f"Height must be between {lo} and {hi} cm.",
        form=form,
        ranges=RANGES)
  if not _in_range("neck_val", neck_cm):
    lo, hi = RANGES["neck_val"]
    return render_template_string(
        PAGE,
        result=None,
        error=f"Neck must be between {lo} and {hi} cm.",
        form=form,
        ranges=RANGES)
  if not _in_range("waist_val", waist_cm):
    lo, hi = RANGES["waist_val"]
    return render_template_string(
        PAGE,
        result=None,
        error=f"Waist must be between {lo} and {hi} cm.",
        form=form,
        ranges=RANGES)
  if sex == "female" and not _in_range("hip_val", hip_cm):
    lo, hi = RANGES["hip_val"]
    return render_template_string(
        PAGE,
        result=None,
        error=f"Hip must be between {lo} and {hi} cm.",
        form=form,
        ranges=RANGES)
  if sex == "male" and hip_cm is not None and not _in_range("hip_val", hip_cm):
    lo, hi = RANGES["hip_val"]
    return render_template_string(
        PAGE,
        result=None,
        error=f"If provided, hip must be between {lo} and {hi} cm.",
        form=form,
        ranges=RANGES)

  # Compute
  result, err = navy_bodyfat_percent(sex, height_cm, neck_cm, waist_cm,
                                     hip_cm if sex == "female" else hip_cm)
  if err:
    return render_template_string(PAGE,
                                  result=None,
                                  error=err,
                                  form=form,
                                  ranges=RANGES)

  return render_template_string(PAGE,
                                result=f"{max(-5.0, min(75.0, result)):.2f}",
                                error=None,
                                form=form,
                                ranges=RANGES)


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)
# Version 1 - Body Fat Calculator
