"""Minimal Flask interface for document Q&A and lead scoring."""

from __future__ import annotations

from flask import Flask, render_template_string, request

from assistant import MGCAssistant
from ml_service import score_lead


app = Flask(__name__)
assistant = MGCAssistant()

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MGC Assistant</title>
  <style>
    :root {
      --bg: #070b12; --panel: #101722; --panel-2: #151e2c;
      --border: #263346; --text: #f4f7fb; --muted: #98a6ba;
      --gold: #d6a84b; --gold-light: #f3cf7a; --green: #4fd1a1;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 12% 8%, rgba(214,168,75,.14), transparent 28rem),
        radial-gradient(circle at 90% 85%, rgba(42,103,142,.13), transparent 30rem), var(--bg);
    }
    .shell { width: min(1080px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 60px; }
    header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 64px; }
    .brand { display: flex; align-items: center; gap: 12px; font-weight: 750; letter-spacing: .02em; }
    .mark {
      display: grid; place-items: center; width: 42px; height: 42px; border-radius: 12px;
      color: #111; background: linear-gradient(135deg, var(--gold-light), var(--gold));
      box-shadow: 0 10px 28px rgba(214,168,75,.2); font-weight: 900;
    }
    .status { color: var(--muted); font-size: .86rem; }
    .status::before { content: ""; display: inline-block; width: 7px; height: 7px; margin-right: 8px; border-radius: 50%; background: var(--green); }
    .hero { max-width: 760px; margin: 0 auto 38px; text-align: center; }
    .eyebrow { color: var(--gold-light); text-transform: uppercase; letter-spacing: .18em; font-size: .76rem; font-weight: 800; }
    h1 { margin: 14px 0 12px; font-size: clamp(2.6rem, 7vw, 5rem); line-height: .98; letter-spacing: -.055em; }
    .hero p { color: var(--muted); font-size: 1.08rem; line-height: 1.7; margin: 0 auto; max-width: 650px; }
    .chooser { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; max-width: 820px; margin: 38px auto; }
    .choice {
      text-align: left; padding: 24px; border: 1px solid var(--border); border-radius: 18px;
      background: linear-gradient(145deg, rgba(21,30,44,.96), rgba(12,18,28,.96)); color: var(--text);
      cursor: pointer; transition: transform .2s, border-color .2s, box-shadow .2s;
    }
    .choice:hover, .choice.active { transform: translateY(-3px); border-color: var(--gold); box-shadow: 0 18px 50px rgba(0,0,0,.3); }
    .choice-icon { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 11px; background: rgba(214,168,75,.12); color: var(--gold-light); font-size: 1.25rem; }
    .choice strong { display: block; font-size: 1.08rem; margin: 18px 0 7px; }
    .choice span:last-child { color: var(--muted); line-height: 1.5; }
    .panel { display: none; max-width: 820px; margin: 28px auto 0; padding: 28px; border: 1px solid var(--border); border-radius: 20px; background: rgba(16,23,34,.94); box-shadow: 0 28px 70px rgba(0,0,0,.3); }
    .panel.active { display: block; animation: reveal .25s ease-out; }
    @keyframes reveal { from { opacity: 0; transform: translateY(8px); } }
    .panel-head { display: flex; gap: 14px; align-items: center; margin-bottom: 24px; }
    .panel h2 { margin: 0; font-size: 1.35rem; }
    .panel-head p { margin: 4px 0 0; color: var(--muted); font-size: .9rem; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    label { display: block; color: #cbd5e3; font-size: .86rem; font-weight: 650; }
    input, select, textarea {
      width: 100%; margin-top: 7px; padding: 12px 13px; border: 1px solid var(--border); border-radius: 10px;
      background: #0b111b; color: var(--text); font: inherit; outline: none; transition: border-color .2s, box-shadow .2s;
    }
    input:focus, select:focus, textarea:focus { border-color: var(--gold); box-shadow: 0 0 0 3px rgba(214,168,75,.1); }
    textarea { resize: vertical; min-height: 120px; }
    .checks { display: grid; gap: 10px; margin-top: 18px; }
    .check { display: flex; align-items: center; gap: 10px; font-weight: 500; }
    .check input { width: 16px; height: 16px; margin: 0; accent-color: var(--gold); }
    .submit { margin-top: 22px; padding: 12px 20px; border: 0; border-radius: 10px; color: #121212; background: linear-gradient(135deg, var(--gold-light), var(--gold)); font-weight: 800; cursor: pointer; }
    .submit:hover { filter: brightness(1.08); }
    .result { margin-top: 22px; padding: 18px; border: 1px solid #314158; border-radius: 12px; background: #0b111b; white-space: pre-wrap; line-height: 1.65; color: #dce5f1; }
    .score { color: var(--gold-light); font-size: 2.2rem; font-weight: 850; letter-spacing: -.04em; }
    .error { color: #ff9c9c; padding: 12px; border: 1px solid #6b3035; border-radius: 10px; background: #251317; }
    footer { color: #69788c; text-align: center; margin-top: 44px; font-size: .8rem; }
    @media (max-width: 680px) { header { margin-bottom: 40px; } .chooser, .grid { grid-template-columns: 1fr; } .panel { padding: 20px; } .status { display: none; } }
  </style>
</head>
<body>
<div class="shell">
  <header>
    <div class="brand"><span class="mark">M</span><span>MGC Assistant</span></div>
    <div class="status">Sales intelligence online</div>
  </header>
  <div class="hero">
    <div class="eyebrow">MGC Developments</div>
    <h1>MGC Assistant</h1>
    <p>Your intelligent workspace for accurate project answers and data-driven lead prioritization.</p>
  </div>
  <div class="chooser">
    <button class="choice{% if active_tab == 'chat' %} active{% endif %}" type="button" data-target="chat">
      <span class="choice-icon">✦</span><strong>Open Document Chat</strong><span>Ask about pricing, policies, payment plans and project details with sources.</span>
    </button>
    <button class="choice{% if active_tab == 'score' %} active{% endif %}" type="button" data-target="score">
      <span class="choice-icon">↗</span><strong>Open Lead Scoring</strong><span>Estimate conversion potential and prioritize the sales team's next calls.</span>
    </button>
  </div>

  <section id="chat" class="panel{% if active_tab == 'chat' %} active{% endif %}">
    <div class="panel-head"><span class="choice-icon">✦</span><div><h2>Document Chat</h2><p>Answers grounded in approved MGC documents</p></div></div>
    <form method="post">
      <input type="hidden" name="action" value="ask">
      <label for="question">Your question</label>
      <textarea id="question" name="question" placeholder="e.g. What is the transfer fee?" required>{{ question }}</textarea>
      <button class="submit" type="submit">Get grounded answer</button>
    </form>
    {% if answer %}
      <div class="result"><strong>Answer:</strong> {{ answer.text }}
{% if answer.evidence %}

<strong>Sources:</strong>{% for source in answer.evidence %}
- {{ source.render() }}{% endfor %}{% endif %}</div>
    {% endif %}
  </section>

  <section id="score" class="panel{% if active_tab == 'score' %} active{% endif %}">
    <div class="panel-head"><span class="choice-icon">↗</span><div><h2>Lead Scoring</h2><p>Leakage-safe conversion ranking using intake-time details</p></div></div>
    <form method="post">
      <input type="hidden" name="action" value="score">
      <div class="grid">
        <label>Lead source <select name="source" required>{% for item in sources %}<option>{{ item }}</option>{% endfor %}</select></label>
        <label>Property type <select name="property_type" required>{% for item in property_types %}<option>{{ item }}</option>{% endfor %}</select></label>
        <label>City <input name="city" value="Islamabad" required></label>
        <label>Area <input name="area" value="B-17"></label>
        <label>Budget (PKR lac) <input name="budget_pkr_lac" type="number" min="0" step="0.1" value="150" required></label>
        <label>Bedrooms <input name="bedrooms" type="number" min="0" max="9" step="1" value="2"></label>
        <label>Agent experience (years) <input name="agent_experience_years" type="number" min="0" step="0.1" value="3"></label>
      </div>
      <div class="checks">
        <label class="check"><input name="is_overseas" type="checkbox" value="1"> Overseas buyer</label>
        <label class="check"><input name="referred_by_existing_client" type="checkbox" value="1"> Referred by existing client</label>
        <label class="check"><input name="has_financing_approved" type="checkbox" value="1"> Financing approved</label>
      </div>
      <button class="submit" type="submit">Calculate lead score</button>
    </form>
    {% if score is not none %}
      <div class="result"><strong>Conversion score</strong><br><span class="score">{{ "%.1f"|format(score * 100) }}%</span>

Use this score to rank leads, not as a guaranteed or calibrated probability.</div>
    {% endif %}
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
  </section>
  <footer>MGC Developments · SM Abdullah | smabdullah.ds@gmail.com</footer>
</div>
<script>
  const choices = document.querySelectorAll('.choice');
  const panels = document.querySelectorAll('.panel');
  choices.forEach(button => button.addEventListener('click', () => {
    const target = button.dataset.target;
    choices.forEach(item => item.classList.toggle('active', item === button));
    panels.forEach(panel => panel.classList.toggle('active', panel.id === target));
    document.getElementById(target).scrollIntoView({ behavior: 'smooth', block: 'start' });
  }));
</script>
</body>
</html>"""


@app.route("/", methods=["GET", "POST"])
def index():
    answer = None
    score = None
    error = None
    question = ""
    active_tab = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "ask":
            active_tab = "chat"
            question = request.form.get("question", "").strip()
            if question:
                answer = assistant.ask(question)
        elif action == "score":
            active_tab = "score"
            try:
                values = {
                    "source": request.form["source"],
                    "city": request.form["city"],
                    "area": request.form.get("area") or None,
                    "property_type": request.form["property_type"],
                    "budget_pkr_lac": float(request.form["budget_pkr_lac"]),
                    "bedrooms": float(request.form["bedrooms"]) if request.form.get("bedrooms") else None,
                    "agent_experience_years": float(request.form["agent_experience_years"]) if request.form.get("agent_experience_years") else None,
                    "is_overseas": int("is_overseas" in request.form),
                    "referred_by_existing_client": int("referred_by_existing_client" in request.form),
                    "has_financing_approved": int("has_financing_approved" in request.form),
                }
                score = score_lead(values)
            except (KeyError, TypeError, ValueError) as exc:
                error = f"Please check the lead values: {exc}"

    return render_template_string(
        PAGE,
        answer=answer,
        score=score,
        error=error,
        question=question,
        active_tab=active_tab,
        sources=["Facebook Ads", "Property Portal", "Google Search", "Instagram", "Referral", "Walk-in", "WhatsApp Campaign", "Expo Stall", "Billboard"],
        property_types=["Apartment", "Plot", "Villa", "Commercial Shop", "Penthouse", "Farmhouse"],
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
