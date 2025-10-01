# main.py
from flask import Flask, request, render_template_string
import math, os

app = Flask(__name__)

# -------- Canonical ranges (server-side truth; metric) --------
RANGES = {
    "age": (13, 80),           # years (kept for record; not used in formula)
    "height_cm": (130.0, 230.0),
    "weight_kg": (35.0, 200.0),  # optional; not used in Navy formula
    "neck_cm": (25.0, 60.0),
    "waist_cm": (50.0, 200.0),
    "hip_cm": (60.0, 200.0),
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
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
      background: radial-gradient(1200px 800px at 80% -20%, #1a2332 0%, #0b0f14 60%);
      color: var(--text);
    }
    .wrap { max-width: 960px; margin: 40px auto; padding: 16px; }
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
    .col-8 { grid-column: span 8; }
    .col-6 { grid-column: span 6; }
    .col-4 { grid-column: span 4; }
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
    input.bad { border-color: var(--danger); box-shadow: 0 0 0 3px #ff6b6b33; }
    .unit-row { display: flex; gap: 10px; flex-wrap: wrap; margin: 8px 0 6px; }
    .radio {
      display: inline-flex; align-items: center; gap: 8px;
      font-size: 13px; color: var(--muted);
      padding: 6px 10px; border: 1px solid #1b2636; border-radius: 999px;
      cursor: pointer; user-select: none;
    }
    .hint { font-size: 12px; color: #9fb0c3; margin-top: 6px; }
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
    @media (max-width: 900px){
      .col-8, .col-6, .col-4 { grid-column: span 12; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>U.S. Navy Body Fat Calculator</h1>
      <p class="muted">Metric or imperial inputs. We convert under the hood, keep you in range, and try not to judge your tape measure skills.</p>

      {% if error %}
        <div class="result err"><strong>Error:</strong> {{ error }}</div>
      {% endif %}
      {% if result is not none %}
        <div class="result ok">
          <div><strong>Estimated Body Fat:</strong> {{ result }}%</div>
          {% if show_weight %}<div class="hint">Note: weight is not used by the Navy formula; included for record only.</div>{% endif %}
        </div>
      {% endif %}

      <form id="calcForm" method="POST" novalidate>
        <div class="grid">
          <!-- Sex -->
          <div class="col-6 field">
            <span class="label">Sex</span>
            <div class="unit-row">
              <label class="radio"><input type="radio" name="sex" value="male" {% if form.sex=='male' or not form.sex %}checked{% endif %}> Male</label>
              <label class="radio"><input type="radio" name="sex" value="female" {% if form.sex=='female' %}checked{% endif %}> Female</label>
            </div>
          </div>

          <!-- Age (kept for record) -->
          <div class="col-6 field">
            <label class="label" for="age">Age (years)</label>
            <input type="number" id="age" name="age" min="{{ ranges.age[0] }}" max="{{ ranges.age[1] }}" step="1" placeholder="e.g., 25" value="{{ form.age or '' }}" inputmode="numeric">
            <div class="hint">Allowed: {{ ranges.age[0] }}–{{ ranges.age[1] }} years</div>
          </div>

          <!-- Height -->
          <div class="col-12"><div class="hint">Height</div></div>
          <div class="col-6 field">
            <span class="label">Unit</span>
            <div class="unit-row">
              <label class="radio"><input type="radio" name="height_unit" value="cm" {% if form.height_unit=='cm' or not form.height_unit %}checked{% endif %} onclick="toggleHeight()"> Centimeters</label>
              <label class="radio"><input type="radio" name="height_unit" value="ftin" {% if form.height_unit=='ftin' %}checked{% endif %} onclick="toggleHeight()"> Feet + Inches</label>
            </div>
            <div id="height_cm_box" style="margin-top:8px;">
              <label class="label" for="height_cm">Height (cm)</label>
              <input type="number" id="height_cm" name="height_cm" step="0.1" placeholder="e.g., 175.0" value="{{ form.height_cm or '' }}" inputmode="decimal">
              <div class="hint">Allowed: {{ ranges.height_cm[0] }}–{{ ranges.height_cm[1] }} cm</div>
            </div>
            <div id="height_ftin_box" style="display:none; margin-top:8px;">
              <div class="grid">
                <div class="col-6">
                  <label class="label" for="height_ft">Feet</label>
                  <input type="number" id="height_ft" name="height_ft" step="1" placeholder="e.g., 5" value="{{ form.height_ft or '' }}" inputmode="numeric">
                </div>
                <div class="col-6">
                  <label class="label" for="height_in">Inches</label>
                  <input type="number" id="height_in" name="height_in" step="0.1" placeholder="e.g., 9.0" value="{{ form.height_in or '' }}" inputmode="decimal">
                </div>
              </div>
              <div class="hint" id="height_range_hint"></div>
            </div>
          </div>

          <!-- Weight (for record; not used in formula) -->
          <div class="col-6 field">
            <span class="label">Weight Unit</span>
            <div class="unit-row">
              <label class="radio"><input type="radio" name="weight_unit" value="kg" {% if form.weight_unit=='kg' or not form.weight_unit %}checked{% endif %} onclick="onUnitToggle()"> kg</label>
              <label class="radio"><input type="radio" name="weight_unit" value="lb" {% if form.weight_unit=='lb' %}checked{% endif %} onclick="onUnitToggle()"> lbs</label>
            </div>
            <div id="weight_box" style="margin-top:8px;">
              <label class="label" for="weight_val">Weight</label>
              <input type="number" id="weight_val" name="weight_val" step="0.1" placeholder="e.g., 70.0" value="{{ form.weight_val or '' }}" inputmode="decimal">
              <div class="hint" id="weight_range_hint"></div>
            </div>
          </div>

          <!-- Neck -->
          <div class="col-6 field">
            <span class="label">Neck Unit</span>
            <div class="unit-row">
              <label class="radio"><input type="radio" name="neck_unit" value="cm" {% if form.neck_unit=='cm' or not form.neck_unit %}checked{% endif %} onclick="onUnitToggle()"> cm</label>
              <label class="radio"><input type="radio" name="neck_unit" value="in" {% if form.neck_unit=='in' %}checked{% endif %} onclick="onUnitToggle()"> in</label>
            </div>
            <label class="label" for="neck_val">Neck circumference</label>
            <input type="number" id="neck_val" name="neck_val" step="0.1" placeholder="e.g., 38.0" value="{{ form.neck_val or '' }}" inputmode="decimal">
            <div class="hint" id="neck_range_hint"></div>
          </div>

          <!-- Waist -->
          <div class="col-6 field">
            <span class="label">Waist Unit</span>
            <div class="unit-row">
              <label class="radio"><input type="radio" name="waist_unit" value="cm" {% if form.waist_unit=='cm' or not form.waist_unit %}checked{% endif %} onclick="onUnitToggle()"> cm</label>
              <label class="radio"><input type="radio" name="waist_unit" value="in" {% if form.waist_unit=='in' %}checked{% endif %} onclick="onUnitToggle()"> in</label>
            </div>
            <label class="label" for="waist_val">Waist circumference</label>
            <input type="number" id="waist_val" name="waist_val" step="0.1" placeholder="e.g., 82.0" value="{{ form.waist_val or '' }}" inputmode="decimal">
            <div class="hint" id="waist_range_hint"></div>
          </div>

          <!-- Hip -->
          <div class="col-6 field">
            <span class="label">Hip Unit</span>
            <div class="unit-row">
              <label class="radio"><input type="radio" name="hip_unit" value="cm" {% if form.hip_unit=='cm' or not form.hip_unit %}checked{% endif %} onclick="onUnitToggle()"> cm</label>
              <label class="radio"><input type="radio" name="hip_unit" value="in" {% if form.hip_unit=='in' %}checked{% endif %} onclick="onUnitToggle()"> in</label>
            </div>
            <label class="label" for="hip_val">Hip circumference <span class="hint">(required for female)</span></label>
            <input type="number" id="hip_val" name="hip_val" step="0.1" placeholder="e.g., 95.0" value="{{ form.hip_val or '' }}" inputmode="decimal">
            <div class="hint" id="hip_range_hint"></div>
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
    // ------- helpers -------
    const ranges = {
      height_cm: {min: {{ ranges.height_cm[0] }}, max: {{ ranges.height_cm[1] }}},
      weight_kg: {min: {{ ranges.weight_kg[0] }}, max: {{ ranges.weight_kg[1] }}},
      neck_cm:   {min: {{ ranges.neck_cm[0] }},   max: {{ ranges.neck_cm[1] }}},
      waist_cm:  {min: {{ ranges.waist_cm[0] }},  max: {{ ranges.waist_cm[1] }}},
      hip_cm:    {min: {{ ranges.hip_cm[0] }},    max: {{ ranges.hip_cm[1] }}},
      age:       {min: {{ ranges.age[0] }},       max: {{ ranges.age[1] }}},
    };
    const cmPerIn = 2.54;
    const kgPerLb = 0.45359237;

    const examples = {
      weight_kg: 70.0,
      neck_cm: 38.0,
      waist_cm: 82.0,
      hip_cm: 95.0
    };

    function clamp(v, lo, hi){ return Math.min(hi, Math.max(lo, v)); }
    function setText(id, txt){ const el = document.getElementById(id); if(el) el.textContent = txt; }
    function setPH(id, txt){ const el = document.getElementById(id); if(el) el.setAttribute('placeholder', txt); }

    function curVal(id){
      const el = document.getElementById(id);
      if(!el || el.value === "") return null;
      const v = parseFloat(el.value);
      return Number.isNaN(v) ? null : v;
    }

    // numeric guards
    function attachNumericGuards(sel){
      document.querySelectorAll(sel).forEach(inp => {
        inp.addEventListener('keydown', function(e){
          const allowed = ["Backspace","Tab","ArrowLeft","ArrowRight","Delete","Enter",".","Home","End"];
          if ((e.key >= "0" && e.key <= "9") || allowed.includes(e.key)) {
            if (e.key === "." && this.value.includes(".")) e.preventDefault();
            return;
          }
          if ((e.ctrlKey || e.metaKey) && ["a","c","v","x","z","y"].includes(e.key.toLowerCase())) return;
          e.preventDefault();
        });
      });
    }
    attachNumericGuards('input[type="number"]');

    // ------- placeholders that follow unit toggles (weight, neck, waist, hip) -------
    function kgToLb(kg){ return kg / kgPerLb; }
    function cmToIn(cm){ return cm / cmPerIn; }

    function updatePlaceholders(){
      // Weight example
      const wUnit = document.querySelector('input[name="weight_unit"]:checked')?.value || 'kg';
      if(wUnit === 'kg'){
        setPH('weight_val', `e.g., ${examples.weight_kg.toFixed(1)}`);
      } else {
        const lb = kgToLb(examples.weight_kg);
        setPH('weight_val', `e.g., ${Math.round(lb)}`);
      }
      // Neck example
      const nUnit = document.querySelector('input[name="neck_unit"]:checked')?.value || 'cm';
      if(nUnit === 'cm'){
        setPH('neck_val', `e.g., ${examples.neck_cm.toFixed(1)}`);
      } else {
        setPH('neck_val', `e.g., ${ (Math.round(cmToIn(examples.neck_cm)*10)/10).toFixed(1) }`);
      }
      // Waist example
      const wU = document.querySelector('input[name="waist_unit"]:checked')?.value || 'cm';
      if(wU === 'cm'){
        setPH('waist_val', `e.g., ${examples.waist_cm.toFixed(1)}`);
      } else {
        setPH('waist_val', `e.g., ${ (Math.round(cmToIn(examples.waist_cm)*10)/10).toFixed(1) }`);
      }
      // Hip example
      const hU = document.querySelector('input[name="hip_unit"]:checked')?.value || 'cm';
      if(hU === 'cm'){
        setPH('hip_val', `e.g., ${examples.hip_cm.toFixed(1)}`);
      } else {
        setPH('hip_val', `e.g., ${ (Math.round(cmToIn(examples.hip_cm)*10)/10).toFixed(1) }`);
      }
    }

    // ------- unit UI/hints -------
    function toggleHeight(){
      const unit = document.querySelector('input[name="height_unit"]:checked')?.value || 'cm';
      const cmBox = document.getElementById('height_cm_box');
      const ftinBox = document.getElementById('height_ftin_box');
      if(unit === 'cm'){ cmBox.style.display = ''; ftinBox.style.display = 'none'; }
      else { cmBox.style.display = 'none'; ftinBox.style.display = ''; }
      updateHints();
      markAllValidity();
    }

    function onUnitToggle(){
      updateHints();
      updatePlaceholders();
      markAllValidity();
    }

    function updateHints(){
      // Height hint (ft/in range)
      const ftRange = cmToFeetInRange(ranges.height_cm.min, ranges.height_cm.max);
      setText('height_range_hint', `Allowed: ${ftRange.min.ft}′${ftRange.min.in.toFixed(1)}″–${ftRange.max.ft}′${ftRange.max.in.toFixed(1)}″`);
      // Weight hint
      const unitW = document.querySelector('input[name="weight_unit"]:checked')?.value || 'kg';
      if(unitW === 'kg'){
        setText('weight_range_hint', `Allowed: ${ranges.weight_kg.min}–${ranges.weight_kg.max} kg`);
      } else {
        const lo = ranges.weight_kg.min / kgPerLb;
        const hi = ranges.weight_kg.max / kgPerLb;
        setText('weight_range_hint', `Allowed: ${lo.toFixed(1)}–${hi.toFixed(1)} lbs`);
      }
      // Neck/Waist/Hip hints
      const nkU = document.querySelector('input[name="neck_unit"]:checked')?.value || 'cm';
      const wsU = document.querySelector('input[name="waist_unit"]:checked')?.value || 'cm';
      const hpU = document.querySelector('input[name="hip_unit"]:checked')?.value || 'cm';
      setText('neck_range_hint',  rangeHint('neck_cm',  nkU));
      setText('waist_range_hint', rangeHint('waist_cm', wsU));
      setText('hip_range_hint',   rangeHint('hip_cm',   hpU));
    }

    function rangeHint(metricKey, unit){
      const {min, max} = ranges[metricKey];
      if(unit === 'cm') return `Allowed: ${min}–${max} cm`;
      const lo = min / cmPerIn;
      const hi = max / cmPerIn;
      return `Allowed: ${lo.toFixed(1)}–${hi.toFixed(1)} in`;
    }

    function cmToFeetIn(cm){
      const totalIn = cm / cmPerIn;
      const ft = Math.floor(totalIn / 12);
      const inch = totalIn - ft*12;
      return {ft, inch};
    }
    function cmToFeetInRange(minCm, maxCm){
      const a = cmToFeetIn(minCm);
      const b = cmToFeetIn(maxCm);
      return {min: {ft:a.ft, in:a.inch}, max:{ft:b.ft, in:b.inch}};
    }

    // ------- validation that respects units -------
    const submitBtn = document.getElementById('submitBtn');

    function isInRangeMetric(v, key){
      const r = ranges[key];
      return v !== null && !Number.isNaN(v) && v >= r.min && v <= r.max;
    }

    function markBad(el, bad){
      if(!el) return;
      if(bad) el.classList.add('bad'); else el.classList.remove('bad');
    }

    function getEffectiveValuesMetric(){
      // Height
      const hUnit = document.querySelector('input[name="height_unit"]:checked')?.value || 'cm';
      let height_cm = null;
      if(hUnit === 'cm'){
        const v = curVal('height_cm');
        height_cm = v;
      } else {
        const ft = curVal('height_ft') || 0;
        const inch = curVal('height_in') || 0;
        const totalIn = ft*12 + inch;
        height_cm = totalIn * cmPerIn;
      }
      // Weight
      const wUnit = document.querySelector('input[name="weight_unit"]:checked')?.value || 'kg';
      let weight_kg = null;
      const w = curVal('weight_val');
      if(w !== null){
        weight_kg = (wUnit === 'kg') ? w : w * kgPerLb;
      }
      // Neck
      const nUnit = document.querySelector('input[name="neck_unit"]:checked')?.value || 'cm';
      let neck_cm = null;
      const n = curVal('neck_val');
      if(n !== null) neck_cm = (nUnit === 'cm') ? n : n * cmPerIn;
      // Waist
      const wU = document.querySelector('input[name="waist_unit"]:checked')?.value || 'cm';
      let waist_cm = null;
      const wv = curVal('waist_val');
      if(wv !== null) waist_cm = (wU === 'cm') ? wv : wv * cmPerIn;
      // Hip
      const hU = document.querySelector('input[name="hip_unit"]:checked')?.value || 'cm';
      let hip_cm = null;
      const hv = curVal('hip_val');
      if(hv !== null) hip_cm = (hU === 'cm') ? hv : hv * cmPerIn;

      // Age
      const age = curVal('age');

      return {age, height_cm, weight_kg, neck_cm, waist_cm, hip_cm};
    }

    function markAllValidity(){
      const eff = getEffectiveValuesMetric();
      // Height
      const hUnit = document.querySelector('input[name="height_unit"]:checked')?.value || 'cm';
      if(hUnit === 'cm'){
        markBad(document.getElementById('height_cm'), !isInRangeMetric(eff.height_cm, 'height_cm'));
      } else {
        const bad = !isInRangeMetric(eff.height_cm, 'height_cm');
        markBad(document.getElementById('height_ft'), bad);
        markBad(document.getElementById('height_in'), bad);
      }
      // Weight (optional; only mark if filled)
      const wBad = (eff.weight_kg !== null) && !isInRangeMetric(eff.weight_kg, 'weight_kg');
      markBad(document.getElementById('weight_val'), wBad);
      // Neck/Waist/Hip
      markBad(document.getElementById('neck_val'),  !isInRangeMetric(eff.neck_cm, 'neck_cm'));
      markBad(document.getElementById('waist_val'), !isInRangeMetric(eff.waist_cm, 'waist_cm'));
      const hipEl = document.getElementById('hip_val');
      if(hipEl.value === "") { markBad(hipEl, false); }
      else { markBad(hipEl, !isInRangeMetric(eff.hip_cm, 'hip_cm')); }
      // Age
      const ageEl = document.getElementById('age');
      if(ageEl.value === "") markBad(ageEl, false);
      else markBad(ageEl, !isInRangeMetric(eff.age, 'age'));

      // Disable submit if any .bad present
      const anyBad = !!document.querySelector('input.bad');
      submitBtn.disabled = anyBad;
    }

    function clampOnBlur(e){
      const id = e.target.id;
      if(id === 'height_ft' || id === 'height_in'){
        const eff = getEffectiveValuesMetric();
        if(eff.height_cm === null) return;
        let cm = clamp(eff.height_cm, ranges.height_cm.min, ranges.height_cm.max);
        const totalIn = cm / cmPerIn;
        const ft = Math.floor(totalIn / 12);
        const inch = (totalIn - ft*12);
        document.getElementById('height_ft').value = ft;
        document.getElementById('height_in').value = Math.round(inch*10)/10;
      }
      markAllValidity();
    }

    function wire(){
      toggleHeight();
      updateHints();
      updatePlaceholders();

      document.querySelectorAll('input[type="number"]').forEach(inp => {
        inp.addEventListener('input', markAllValidity);
        inp.addEventListener('blur', clampOnBlur);
      });
      ['height_unit','weight_unit','neck_unit','waist_unit','hip_unit'].forEach(name => {
        document.querySelectorAll(`input[name="${name}"]`).forEach(r => r.addEventListener('change', onUnitToggle));
      });

      document.getElementById('resetBtn').addEventListener('click', function(){
        const form = document.getElementById('calcForm');
        form.reset();
        document.querySelectorAll('.result').forEach(n => n.remove());
        document.querySelectorAll('input.bad').forEach(el => el.classList.remove('bad'));
        submitBtn.disabled = false;
        toggleHeight(); updateHints(); updatePlaceholders();
      });

      markAllValidity();
    }

    wire();
  </script>
</body>
</html>
"""

def to_inches(val, unit):
    if val is None:
        return None
    return val / 2.54 if unit == "cm" else val

def height_to_inches(height_unit, cm, ft, inch):
    if height_unit == "cm":
        return None if cm is None else cm / 2.54
    ftv = ft or 0.0
    inv = inch or 0.0
    total_in = ftv * 12.0 + inv
    return None if total_in == 0 else total_in

def navy_bodyfat_percent(sex, height_in, neck_in, waist_in, hip_in=None):
    if sex == "male":
        if any(v is None for v in [height_in, neck_in, waist_in]):
            return None, "Missing required measurements for male."
        x = waist_in - neck_in
        if x <= 0 or height_in <= 0:
            return None, "For male, waist must be greater than neck, and height must be positive."
        bf = 86.010 * math.log10(x) - 70.041 * math.log10(height_in) + 36.76
        return round(bf, 2), None
    else:
        if any(v is None for v in [height_in, neck_in, waist_in, hip_in]):
            return None, "Missing required measurements for female."
        x = waist_in + hip_in - neck_in
        if x <= 0 or height_in <= 0:
            return None, "For female, waist + hip must be greater than neck, and height must be positive."
        bf = 163.205 * math.log10(x) - 97.684 * math.log10(height_in) - 78.387
        return round(bf, 2), None

def _in_range_metric(name, value):
    lo, hi = RANGES[name]
    return value is not None and lo <= value <= hi

@app.route("/", methods=["GET","POST"])
def index():
    form = {
        "sex": request.form.get("sex",""),
        "age": request.form.get("age",""),

        "height_unit": request.form.get("height_unit",""),
        "height_cm": request.form.get("height_cm",""),
        "height_ft": request.form.get("height_ft",""),
        "height_in": request.form.get("height_in",""),

        "weight_unit": request.form.get("weight_unit",""),
        "weight_val": request.form.get("weight_val",""),

        "neck_unit": request.form.get("neck_unit",""),
        "neck_val": request.form.get("neck_val",""),

        "waist_unit": request.form.get("waist_unit",""),
        "waist_val": request.form.get("waist_val",""),

        "hip_unit": request.form.get("hip_unit",""),
        "hip_val": request.form.get("hip_val",""),
    }

    if request.method == "GET":
        return render_template_string(PAGE, result=None, error=None, form=form, ranges=RANGES, show_weight=False)

    def parse_float(s):
        if s in ("", None): return None
        try: return float(s)
        except ValueError: return None

    sex = form["sex"] if form["sex"] in ("male","female") else "male"

    # Age (optional but we check range if provided)
    age = parse_float(form["age"])

    # Height
    h_unit = form["height_unit"] if form["height_unit"] in ("cm","ftin") else "cm"
    height_cm = None
    if h_unit == "cm":
        height_cm = parse_float(form["height_cm"])
    else:
        ft = parse_float(form["height_ft"]) or 0.0
        inc = parse_float(form["height_in"]) or 0.0
        total_in = ft*12.0 + inc
        height_cm = total_in * 2.54 if total_in > 0 else None

    # Weight (optional; not used in calc)
    weight_unit = form["weight_unit"] if form["weight_unit"] in ("kg","lb") else "kg"
    weight_val = parse_float(form["weight_val"])
    weight_kg = None if weight_val is None else (weight_val if weight_unit=="kg" else weight_val*0.45359237)

    # Neck/Waist/Hip
    neck_cm = None
    waist_cm = None
    hip_cm = None

    neck_v = parse_float(form["neck_val"])
    if neck_v is not None:
        neck_cm = neck_v if form["neck_unit"] == "cm" else neck_v*2.54

    waist_v = parse_float(form["waist_val"])
    if waist_v is not None:
        waist_cm = waist_v if form["waist_unit"] == "cm" else waist_v*2.54

    hip_v = parse_float(form["hip_val"])
    if hip_v is not None:
        hip_cm = hip_v if form["hip_unit"] == "cm" else hip_v*2.54

    # Presence checks for formula fields
    if height_cm is None:
        return render_template_string(PAGE, result=None, error="Please enter your height.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if neck_cm is None:
        return render_template_string(PAGE, result=None, error="Please enter your neck circumference.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if waist_cm is None:
        return render_template_string(PAGE, result=None, error="Please enter your waist circumference.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if sex == "female" and hip_cm is None:
        return render_template_string(PAGE, result=None, error="Please enter your hip circumference.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))

    # Range checks (metric)
    if age is not None and not _in_range_metric("age", age):
        lo, hi = RANGES["age"];   return render_template_string(PAGE, result=None, error=f"Age must be between {lo} and {hi}.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if not _in_range_metric("height_cm", height_cm):
        lo, hi = RANGES["height_cm"]; return render_template_string(PAGE, result=None, error=f"Height must be between {lo:.0f} and {hi:.0f} cm.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if not _in_range_metric("neck_cm", neck_cm):
        lo, hi = RANGES["neck_cm"];   return render_template_string(PAGE, result=None, error=f"Neck must be between {lo:.0f} and {hi:.0f} cm.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if not _in_range_metric("waist_cm", waist_cm):
        lo, hi = RANGES["waist_cm"];  return render_template_string(PAGE, result=None, error=f"Waist must be between {lo:.0f} and {hi:.0f} cm.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if sex == "female" and not _in_range_metric("hip_cm", hip_cm):
        lo, hi = RANGES["hip_cm"];    return render_template_string(PAGE, result=None, error=f"Hip must be between {lo:.0f} and {hi:.0f} cm.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if sex == "male" and hip_cm is not None and not _in_range_metric("hip_cm", hip_cm):
        lo, hi = RANGES["hip_cm"];    return render_template_string(PAGE, result=None, error=f"If provided, hip must be between {lo:.0f} and {hi:.0f} cm.", form=form, ranges=RANGES, show_weight=(weight_kg is not None))
    if weight_kg is not None and not _in_range_metric("weight_kg", weight_kg):
        lo, hi = RANGES["weight_kg"]; return render_template_string(PAGE, result=None, error=f"Weight must be between {lo:.0f} and {hi:.0f} kg.", form=form, ranges=RANGES, show_weight=True)

    # Convert to inches for formula
    height_in = height_cm / 2.54
    neck_in   = neck_cm / 2.54
    waist_in  = waist_cm / 2.54
    hip_in    = None if hip_cm is None else hip_cm / 2.54

    # Compute
    result, err = navy_bodyfat_percent(sex, height_in, neck_in, waist_in, hip_in)
    if err:
        return render_template_string(PAGE, result=None, error=err, form=form, ranges=RANGES, show_weight=(weight_kg is not None))

    return render_template_string(PAGE, result=f"{max(-5.0, min(75.0, result)):.2f}", error=None, form=form, ranges=RANGES, show_weight=(weight_kg is not None))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
