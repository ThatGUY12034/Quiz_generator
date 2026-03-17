/* ═══════════════════════════════════════════════
   QuizGenius — Frontend Logic (Updated for .env support)
═══════════════════════════════════════════════ */

// ── State ──────────────────────────────────────
let state = {
  questions:    [],
  answers:      {},      // { question_id: selected_answer }
  current:      0,
  timerInterval: null,
  seconds:      0,
  activeTab:    'topic',
  pdfText:      '',
  envKeyConfigured: false, // Whether .env has API key
};

// ── Screen Navigation ──────────────────────────
function showScreen(name) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(`screen-${name}`).classList.add('active');
  window.scrollTo(0, 0);
}

// ── Tab switching ──────────────────────────────
function switchTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.add('active');
}

// ── Pill toggle ────────────────────────────────
function setPill(groupId, btn) {
  document.querySelectorAll(`#${groupId} .pill`).forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
}

// ── Check if API key is in .env ─────────────────
// ── Check if API key is in .env ─────────────────
async function checkEnvKey() {
  try {
    const response = await fetch('/api/models');
    const data = await response.json();
    
    if (data.env_key_configured) {
      state.envKeyConfigured = true;
      // Simply hide the API key container without showing any message
      document.getElementById('api-key-container').style.display = 'none';
      
      // Remove required attribute from hidden input
      document.getElementById('api-key').required = false;
    } else {
      // Make API key required if no env key
      document.getElementById('api-key').required = true;
      // Show the API key container
      document.getElementById('api-key-container').style.display = 'block';
    }
  } catch (error) {
    console.error('Failed to check env key:', error);
    // Make API key required if we can't check env
    document.getElementById('api-key').required = true;
    document.getElementById('api-key-container').style.display = 'block';
  }
}

// ── Load models on startup ─────────────────────
async function loadModels() {
  try {
    const response = await fetch('/api/models');
    const data = await response.json();
    
    const modelSelect = document.getElementById('model-select');
    if (modelSelect) {
      modelSelect.innerHTML = '';
      data.models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = `${model.name} - ${model.description} (${model.context})`;
        modelSelect.appendChild(option);
      });
    }
    
    // Check if API key is in .env
    await checkEnvKey();
    
  } catch (error) {
    console.error('Failed to load models:', error);
  }
}

// ── PDF Upload ─────────────────────────────────
async function handlePDF(event) {
  const file = event.target.files[0];
  if (!file) return;

  const status = document.getElementById('pdf-status');
  const textarea = document.getElementById('pdf-text');

  status.textContent = '⏳ Extracting text from PDF...';
  status.className = 'pdf-status success';
  status.classList.remove('hidden');

  const formData = new FormData();
  formData.append('pdf', file);

  try {
    const res  = await fetch('/api/upload-pdf', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.error) {
      status.textContent = '❌ ' + data.error;
      status.className = 'pdf-status error';
      return;
    }

    state.pdfText = data.text;
    status.textContent = `✅ PDF loaded — ${data.text.length.toLocaleString()} characters extracted.`;
    status.className = 'pdf-status success';
    textarea.value = data.preview + (data.text.length > 3000 ? '\n\n[... more content ...]' : '');
    textarea.classList.remove('hidden');
  } catch (e) {
    status.textContent = '❌ Upload failed. Try again.';
    status.className = 'pdf-status error';
  }
}

// ── Get content based on active tab ───────────
function getContent() {
  switch (state.activeTab) {
    case 'topic':  return { content: document.getElementById('topic-input').value.trim(), type: 'topic' };
    case 'text':   return { content: document.getElementById('text-input').value.trim(),  type: 'text' };
    case 'pdf':    return { content: state.pdfText, type: 'PDF document' };
    default:       return { content: '', type: 'topic' };
  }
}

// ── Form Submit ────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  const form = document.getElementById('quiz-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      console.log('Form submitted'); // Debug log

      // Get API key from form OR use environment variable
      const apiKeyInput = document.getElementById('api-key');
      const apiKey = apiKeyInput ? apiKeyInput.value.trim() : '';
      
      const modelSelect = document.getElementById('model-select');
      const model = modelSelect ? modelSelect.value : 'models/gemini-2.5-flash';
      
      const { content, type } = getContent();
      
      const numPill = document.querySelector('#num-group .pill.active');
      const numQ = numPill ? numPill.dataset.val : '10';
      
      const diffPill = document.querySelector('#diff-group .pill.active');
      const diff = diffPill ? diffPill.dataset.val : 'Medium';
      
      const qTypes = [...document.querySelectorAll('input[name="qtype"]:checked')].map(i => i.value);
      
      const languageSelect = document.getElementById('language-select');
      const language = languageSelect ? languageSelect.value : 'English';
      
      const errorDiv = document.getElementById('form-error');
      const genBtn = document.getElementById('generate-btn');
      const genText = document.getElementById('gen-text');
      const genLoader = document.getElementById('gen-loader');

      errorDiv.classList.add('hidden');

      // Validate
      if (!apiKey && !state.envKeyConfigured) {
        errorDiv.textContent = '⚠️ Please enter your Gemini API key or add it to .env file.';
        errorDiv.classList.remove('hidden');
        return;
      }
      
      if (!content) {
        errorDiv.textContent = '⚠️ Please provide a topic, text, or PDF.';
        errorDiv.classList.remove('hidden');
        return;
      }
      
      if (qTypes.length === 0) {
        errorDiv.textContent = '⚠️ Please select at least one question type.';
        errorDiv.classList.remove('hidden');
        return;
      }

      if (!model) {
        errorDiv.textContent = '⚠️ Please select a model.';
        errorDiv.classList.remove('hidden');
        return;
      }

      // Loading state
      genBtn.disabled = true;
      genText.classList.add('hidden');
      genLoader.classList.remove('hidden');

      try {
        console.log('Sending request to /api/generate'); // Debug log
        const res  = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            api_key:        apiKey,  // Will be empty if using env key
            model:          model,
            input_type:     type,
            content:        content,
            num_questions:  parseInt(numQ),
            difficulty:     diff,
            question_types: qTypes,
            language:       language
          })
        });

        const data = await res.json();
        console.log('Response received:', data); // Debug log

        if (data.error) {
          errorDiv.textContent = '⚠️ ' + data.error;
          errorDiv.classList.remove('hidden');
          return;
        }

        // Start quiz
        state.questions = data.questions;
        state.answers   = {};
        state.current   = 0;
        
        // Show which key source was used
        const keySource = data.key_source === 'environment' ? '(using .env key)' : '';
        startQuiz(content, diff, keySource);

      } catch (err) {
        console.error('Generation error:', err);
        errorDiv.textContent = '⚠️ Network error. Make sure the server is running.';
        errorDiv.classList.remove('hidden');
      } finally {
        genBtn.disabled = false;
        genText.classList.remove('hidden');
        genLoader.classList.add('hidden');
      }
    });
  }
});

// ── Start Quiz ─────────────────────────────────
function startQuiz(topicLabel, difficulty, keySource = '') {
  const label = topicLabel.length > 30 ? topicLabel.slice(0,30) + '…' : topicLabel;
  document.getElementById('quiz-topic-label').textContent = label + ' · ' + difficulty + ' ' + keySource;

  buildNavDots();
  renderQuestion();
  startTimer();
  showScreen('quiz');
}

// ── Build nav dots ─────────────────────────────
function buildNavDots() {
  const container = document.getElementById('nav-dots');
  container.innerHTML = '';
  state.questions.forEach((_, i) => {
    const dot = document.createElement('div');
    dot.className = 'nav-dot';
    dot.onclick = () => goToQuestion(i);
    container.appendChild(dot);
  });
  updateNavDots();
}

function updateNavDots() {
  const dots = document.querySelectorAll('.nav-dot');
  dots.forEach((dot, i) => {
    dot.classList.remove('answered', 'current');
    if (i === state.current) dot.classList.add('current');
    else if (state.answers[state.questions[i]?.id] !== undefined) dot.classList.add('answered');
  });
}

// ── Render Question ────────────────────────────
function renderQuestion() {
  if (!state.questions || state.questions.length === 0) return;
  
  const q     = state.questions[state.current];
  const total = state.questions.length;

  document.getElementById('q-counter').textContent = `${state.current + 1} / ${total}`;
  document.getElementById('quiz-progress').style.width = `${((state.current + 1) / total) * 100}%`;

  // Type badge
  const typeMap = { mcq: 'MCQ', truefalse: 'True / False', fillblank: 'Fill in the Blank' };
  document.getElementById('q-type-badge').textContent = typeMap[q.type] || q.type.toUpperCase();

  // Question text
  document.getElementById('q-text').textContent = q.question;

  // Options
  const optsEl   = document.getElementById('q-options');
  const fillEl   = document.getElementById('fill-input');
  const savedAns = state.answers[q.id];

  optsEl.innerHTML = '';
  fillEl.classList.add('hidden');

  if (q.type === 'fillblank') {
    fillEl.classList.remove('hidden');
    fillEl.value = savedAns || '';
    fillEl.oninput = () => { 
      state.answers[q.id] = fillEl.value.trim(); 
      updateNavDots(); 
    };
  } else {
    q.options.forEach(opt => {
      const btn = document.createElement('button');
      btn.className = 'opt-btn';
      btn.textContent = opt;
      btn.onclick = () => selectOption(btn, opt, q.id);
      if (savedAns === opt) btn.classList.add('selected');
      optsEl.appendChild(btn);
    });
  }

  // Nav buttons
  document.getElementById('btn-prev').disabled = state.current === 0;
  document.getElementById('btn-next').style.display = state.current === total - 1 ? 'none' : 'inline-block';
  document.getElementById('btn-submit').style.display = state.current === total - 1 ? 'block' : 'none';

  updateNavDots();
}

// ── Select Option ──────────────────────────────
function selectOption(btn, opt, questionId) {
  document.querySelectorAll('.opt-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  state.answers[questionId] = opt;
  updateNavDots();
}

// ── Navigation ─────────────────────────────────
function nextQuestion() {
  if (state.current < state.questions.length - 1) {
    state.current++;
    renderQuestion();
  }
}
function prevQuestion() {
  if (state.current > 0) {
    state.current--;
    renderQuestion();
  }
}
function goToQuestion(i) {
  state.current = i;
  renderQuestion();
}

// ── Timer ──────────────────────────────────────
function startTimer() {
  state.seconds = 0;
  clearInterval(state.timerInterval);
  state.timerInterval = setInterval(() => {
    state.seconds++;
    const m = String(Math.floor(state.seconds / 60)).padStart(2, '0');
    const s = String(state.seconds % 60).padStart(2, '0');
    document.getElementById('timer').textContent = `⏱ ${m}:${s}`;
  }, 1000);
}
function stopTimer() {
  clearInterval(state.timerInterval);
  const m = String(Math.floor(state.seconds / 60)).padStart(2, '0');
  const s = String(state.seconds % 60).padStart(2, '0');
  return `${m}:${s}`;
}

// ── Submit Quiz ────────────────────────────────
async function submitQuiz() {
  const elapsed = stopTimer();

  // Build answers map { id: answer }
  const answersMap = {};
  state.questions.forEach(q => {
    answersMap[q.id] = state.answers[q.id] || '';
  });

  try {
    const res  = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ questions: state.questions, answers: answersMap })
    });
    const data = await res.json();

    if (data.error) { 
      alert(data.error); 
      return; 
    }

    showResults(data, elapsed);
  } catch (err) {
    console.error('Evaluation error:', err);
    alert('Evaluation error. Try again.');
  }
}

// ── Show Results ───────────────────────────────
function showResults(data, elapsed) {
  const { score, total, percentage, results, feedback } = data;

  // Score ring
  document.getElementById('score-num').textContent = score;
  document.getElementById('score-den').textContent = `/${total}`;
  document.getElementById('results-pct').textContent = `${percentage}%`;
  document.getElementById('results-time').textContent = `Time: ${elapsed}`;
  document.getElementById('results-feedback').textContent = feedback || '';

  // Grade
  let grade = '😞 Needs Work';
  if (percentage === 100) grade = '🏆 Perfect!';
  else if (percentage >= 80) grade = '🌟 Excellent!';
  else if (percentage >= 60) grade = '👍 Good Job!';
  else if (percentage >= 40) grade = '📚 Keep Going';
  document.getElementById('grade-badge').textContent = grade;

  // Stats
  const skipped = results.filter(r => !state.answers[r.id]).length;
  document.getElementById('stat-correct').textContent = score;
  document.getElementById('stat-wrong').textContent   = total - score - skipped;
  document.getElementById('stat-skip').textContent    = skipped;

  // Animate ring
  setTimeout(() => {
    const circumference = 339.3;
    const offset = circumference - (percentage / 100) * circumference;
    document.getElementById('ring-fill').style.strokeDashoffset = offset;
  }, 100);

  // Review list
  const reviewEl = document.getElementById('review-list');
  reviewEl.innerHTML = '';
  results.forEach(r => {
    const div = document.createElement('div');
    div.className = `review-item ${r.is_correct ? 'ok' : 'bad'}`;
    const userAns = r.user_answer || '<em>Skipped</em>';
    div.innerHTML = `
      <div class="ri-status">${r.is_correct ? '✓ CORRECT' : '✗ INCORRECT'}</div>
      <div class="ri-q">${r.question}</div>
      <div class="ri-ans">
        <span class="ri-your">Your answer: <span>${userAns}</span></span>
        ${!r.is_correct ? `<span class="ri-correct">Correct: <span>${r.correct_answer}</span></span>` : ''}
      </div>
      ${r.explanation ? `<div class="ri-explain">💡 ${r.explanation}</div>` : ''}
    `;
    reviewEl.appendChild(div);
  });

  showScreen('results');
}

// ── Retake ─────────────────────────────────────
function retakeQuiz() {
  state.answers = {};
  state.current = 0;
  buildNavDots();
  renderQuestion();
  startTimer();
  document.getElementById('ring-fill').style.strokeDashoffset = 339.3;
  showScreen('quiz');
}

// ── New Quiz ───────────────────────────────────
function newQuiz() {
  showScreen('create');
  state.questions = [];
  state.answers = {};
  state.current = 0;
  stopTimer();
}

// ── Initialize on page load ───────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadModels();
  
  // Set up tab switching
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const tabName = tab.dataset.tab;
      if (tabName) switchTab(tabName);
    });
  });
});