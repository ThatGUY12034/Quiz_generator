from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import PyPDF2
import json
import os
import re
import uuid
import google.generativeai as genai
import traceback
from dotenv import load_dotenv
import logging
import tempfile

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "quiz-generator-secret-2024")
CORS(app)

# ──────────────────────────────────────────────
# Vercel-compatible file handling
# ──────────────────────────────────────────────
IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') is not None
IS_RENDER = os.environ.get('RENDER') == 'true'

# Use /tmp for file uploads on Vercel (writable), otherwise use local uploads folder
if IS_VERCEL:
    UPLOAD_FOLDER = "/tmp/uploads"
    print("Running on Vercel - using /tmp for uploads")
else:
    UPLOAD_FOLDER = "uploads"
    print("Running locally - using local uploads folder")

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Get API key from environment variable
ENV_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


# ──────────────────────────────────────────────
# Free Gemini Models (Updated with Gemini 2.5)
# ──────────────────────────────────────────────
FREE_GEMINI_MODELS = {
    "models/gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "description": "Latest fast model - best for quick quizzes",
        "context": "1M tokens",
        "free_tier": True,
        "provider": "Google Gemini",
        "api_name": "gemini-2.5-flash"
    },
    "models/gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "description": "Advanced model for complex quizzes",
        "context": "2M tokens",
        "free_tier": True,
        "provider": "Google Gemini",
        "api_name": "gemini-2.5-pro"
    },
    "models/gemini-2.5-flash-lite": {
        "name": "Gemini 2.5 Flash-Lite",
        "description": "Lightweight fast model - efficient for basic quizzes",
        "context": "1M tokens",
        "free_tier": True,
        "provider": "Google Gemini",
        "api_name": "gemini-2.5-flash-lite"
    },
    "models/gemini-2.0-flash": {
        "name": "Gemini 2.0 Flash",
        "description": "Stable, reliable model",
        "context": "1M tokens",
        "free_tier": True,
        "provider": "Google Gemini",
        "api_name": "gemini-2.0-flash"
    },
    "models/gemini-2.0-flash-lite": {
        "name": "Gemini 2.0 Flash-Lite",
        "description": "Efficient model for basic quizzes",
        "context": "1M tokens",
        "free_tier": True,
        "provider": "Google Gemini",
        "api_name": "gemini-2.0-flash-lite"
    },
    "models/gemini-flash-latest": {
        "name": "Gemini Flash Latest",
        "description": "Always the latest flash model",
        "context": "1M tokens",
        "free_tier": True,
        "provider": "Google Gemini",
        "api_name": "gemini-flash-latest"
    },
    "models/gemini-pro-latest": {
        "name": "Gemini Pro Latest",
        "description": "Always the latest pro model",
        "context": "2M tokens",
        "free_tier": True,
        "provider": "Google Gemini",
        "api_name": "gemini-pro-latest"
    }
}

# ──────────────────────────────────────────────
# Gemma Models (Google's open models)
# ──────────────────────────────────────────────
GEMMA_MODELS = {
    "models/gemma-3-27b-it": {
        "name": "Gemma 3 27B",
        "description": "Google's open model - 27B parameters, high quality",
        "context": "8K tokens",
        "free_tier": True,
        "provider": "Google Gemma",
        "api_name": "gemma-3-27b-it"
    },
    "models/gemma-3-12b-it": {
        "name": "Gemma 3 12B",
        "description": "Google's open model - 12B parameters, balanced",
        "context": "8K tokens",
        "free_tier": True,
        "provider": "Google Gemma",
        "api_name": "gemma-3-12b-it"
    },
    "models/gemma-3-4b-it": {
        "name": "Gemma 3 4B",
        "description": "Google's open model - 4B parameters, fast",
        "context": "8K tokens",
        "free_tier": True,
        "provider": "Google Gemma",
        "api_name": "gemma-3-4b-it"
    },
    "models/gemma-3-1b-it": {
        "name": "Gemma 3 1B",
        "description": "Google's open model - 1B parameters, very fast",
        "context": "8K tokens",
        "free_tier": True,
        "provider": "Google Gemma",
        "api_name": "gemma-3-1b-it"
    }
}

# Combine all models
ALL_MODELS = {**FREE_GEMINI_MODELS, **GEMMA_MODELS}


# ──────────────────────────────────────────────
# Helper: call Gemini API with increased token limit
# ──────────────────────────────────────────────
def call_gemini(prompt: str, api_key: str, model: str) -> str:
    """Call Google's Gemini API with the specified model"""
    try:
        genai.configure(api_key=api_key)
        
        # Extract the actual model name from the full ID if needed
        if model.startswith("models/"):
            model_name = model
        else:
            model_name = f"models/{model}"
            
        print(f"Using model: {model_name}")
        
        # Get the API name from our models dict if available
        for model_id, model_info in ALL_MODELS.items():
            if model_id == model or model_info["api_name"] == model:
                model_name = model_id
                break
        
        gemini_model = genai.GenerativeModel(model_name)
        
        # Safety settings for educational content
        safety_settings = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_ONLY_HIGH",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_ONLY_HIGH",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_ONLY_HIGH",
        }
        
        # INCREASED max_output_tokens to 8192 for longer responses
        response = gemini_model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
        
        # Check if response was blocked
        if not response.parts:
            block_reason = response.prompt_feedback.block_reason
            raise ValueError(f"Response blocked due to: {block_reason}")
        
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        print(traceback.format_exc())
        raise e


# ──────────────────────────────────────────────
# Helper: extract text from PDF (Vercel-compatible)
# ──────────────────────────────────────────────
def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF with better error handling"""
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except:
                    raise ValueError("Encrypted PDF - please provide an unencrypted PDF")
            
            # Extract text from each page
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"--- Page {page_num + 1} ---\n{page_text}\n"
                    
    except PyPDF2.errors.PdfReadError:
        raise ValueError("Invalid or corrupted PDF file")
    except Exception as e:
        raise ValueError(f"Error reading PDF: {str(e)}")
    
    return text.strip()


# ──────────────────────────────────────────────
# Helper: extract JSON from text (more robust)
# ──────────────────────────────────────────────
def extract_json_from_text(text: str) -> dict:
    """Extract JSON from text with multiple fallback methods"""
    
    # Method 1: Try to find JSON array between ```json and ``` markers
    json_pattern = r'```(?:json)?\s*(\[[\s\S]*?\])\s*```'
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass
    
    # Method 2: Find the largest JSON array in the text
    array_pattern = r'(\[[\s\S]*\])'
    matches = re.findall(array_pattern, text, re.DOTALL)
    
    for potential_json in matches:
        # Try to balance brackets
        open_brackets = potential_json.count('[')
        close_brackets = potential_json.count(']')
        
        if open_brackets > close_brackets:
            # Add missing closing brackets
            potential_json += ']' * (open_brackets - close_brackets)
        
        try:
            return json.loads(potential_json)
        except:
            continue
    
    # Method 3: Manual fixing - try to find where JSON starts and ends
    start_idx = text.find('[')
    if start_idx != -1:
        # Find the last ']' that might close the array
        end_idx = text.rfind(']')
        if end_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx:end_idx+1]
            try:
                return json.loads(json_str)
            except:
                pass
    
    raise ValueError("Could not extract valid JSON from response")


# ──────────────────────────────────────────────
# Helper: build quiz prompt with JSON-only instruction
# ──────────────────────────────────────────────
def build_prompt(content: str, input_type: str, num_questions: int,
                 difficulty: str, question_types: list, language: str = "English") -> str:
    """Build a detailed prompt for the AI"""
    
    types_str = ", ".join(question_types)
    
    difficulty_instructions = {
        "Easy": "Use basic concepts and straightforward questions. Keep language simple.",
        "Medium": "Mix of basic and intermediate concepts. Include some analytical questions.",
        "Hard": "Use complex concepts, require deep understanding and critical thinking.",
        "Expert": "Challenge with advanced topics, require expertise and detailed explanations."
    }
    
    return f"""You are an expert quiz generator. Return ONLY a valid JSON array. No other text, no markdown, no explanations.

Generate {num_questions} {difficulty.lower()} difficulty questions about this {input_type}:

CONTENT:
{content}

QUESTION TYPES: {types_str}

RULES:
- Return ONLY a JSON array, nothing else
- For MCQ: include exactly 4 options with A), B), C), D) prefixes
- For True/False: options = ["True", "False"]
- For Fill in Blank: use _____ for blanks
- Include "id" (number), "type", "question", "options" (array), "answer" (string), "explanation" (string)

Example format:
[
  {{
    "id": 1,
    "type": "mcq",
    "question": "Sample question?",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "answer": "A) Option 1",
    "explanation": "Explanation here"
  }}
]

IMPORTANT: Return ONLY the JSON array. No other text."""


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/models", methods=["GET"])
def list_models():
    """Return available free Gemini and Gemma models"""
    models_list = []
    for model_id, model_info in ALL_MODELS.items():
        models_list.append({
            "id": model_id,
            "name": model_info["name"],
            "description": model_info["description"],
            "context": model_info["context"],
            "free_tier": model_info["free_tier"],
            "provider": model_info["provider"],
            "api_name": model_info["api_name"]
        })
    
    # Sort models by name
    models_list.sort(key=lambda x: x["name"])
    
    return jsonify({
        "models": models_list,
        "total_models": len(models_list),
        "note": "Free tier models - Gemini 2.5 and Gemma 3 series",
        "env_key_configured": bool(ENV_GEMINI_API_KEY)  # Let frontend know if env key exists
    })


@app.route("/api/generate", methods=["POST"])
def generate_quiz():
    """Generate quiz using Gemini models"""
    try:
        data = request.get_json()

        # Get API key - first try from request, then from environment
        api_key = data.get("api_key", "").strip()
        if not api_key and ENV_GEMINI_API_KEY:
            api_key = ENV_GEMINI_API_KEY
            print("Using API key from environment variable")
        
        model = data.get("model", "models/gemini-2.5-flash").strip()
        input_type = data.get("input_type", "topic")
        content = data.get("content", "").strip()
        num_q = int(data.get("num_questions", 5))
        difficulty = data.get("difficulty", "Medium")
        q_types = data.get("question_types", ["mcq"])
        language = data.get("language", "English")

        print(f"API Key present: {bool(api_key)}")
        print(f"Model: {model}")
        print(f"Content length: {len(content)}")
        print(f"Question types: {q_types}")

        # Validate inputs
        if not api_key:
            return jsonify({"error": "Gemini API key is required. Either add it to .env file or enter it in the form."}), 400
        
        if not content:
            return jsonify({"error": "Content or topic is required."}), 400
        
        if not q_types:
            return jsonify({"error": "Select at least one question type."}), 400
        
        if model not in ALL_MODELS:
            return jsonify({"error": f"Unsupported model '{model}'. Choose from available models."}), 400
        
        if num_q < 1 or num_q > 20:
            return jsonify({"error": "Number of questions must be between 1 and 20"}), 400

        # Truncate content if too long
        max_content_length = 30000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "... [content truncated due to length]"

        # Build prompt and call Gemini
        prompt = build_prompt(content, input_type, num_q, difficulty, q_types, language)
        print(f"Prompt built, length: {len(prompt)}")
        
        try:
            raw = call_gemini(prompt, api_key, model)
            print(f"Gemini response received, length: {len(raw)}")
            print(f"First 200 chars of response: {raw[:200]}")
            print(f"Last 200 chars of response: {raw[-200:]}")
        except Exception as e:
            print(f"Gemini call failed: {str(e)}")
            print(traceback.format_exc())
            error_msg = str(e).lower()
            if "api key" in error_msg or "api_key" in error_msg or "permission" in error_msg:
                return jsonify({"error": "Invalid Gemini API key. Please check your key in .env file or the form."}), 401
            elif "quota" in error_msg or "rate limit" in error_msg:
                return jsonify({"error": "Rate limit reached. Please try again in a few minutes."}), 429
            elif "not found" in error_msg or "does not exist" in error_msg:
                return jsonify({"error": f"Model '{model}' is not available. Please try a different model."}), 400
            else:
                return jsonify({"error": f"Gemini API error: {str(e)}"}), 500

        # Extract JSON using robust method
        try:
            questions = extract_json_from_text(raw)
            print(f"Successfully extracted {len(questions)} questions")
        except Exception as e:
            print(f"JSON extraction failed: {str(e)}")
            print(f"Full raw response: {raw}")
            
            # Fallback: try to manually fix incomplete JSON
            if raw.strip().startswith('[') and raw.strip().endswith(','):
                # Try adding closing brackets
                fixed_json = raw.strip() + ']' * (raw.count('[') - raw.count(']'))
                try:
                    questions = json.loads(fixed_json)
                    print("Fixed JSON by adding brackets")
                except:
                    return jsonify({
                        "error": "Failed to parse quiz from AI. The response was incomplete.",
                        "details": str(e),
                        "raw_response_preview": raw[:500] + "..."
                    }), 500
            else:
                return jsonify({
                    "error": "Failed to parse quiz from AI. The response wasn't valid JSON.",
                    "details": str(e),
                    "raw_response_preview": raw[:500] + "..."
                }), 500
        
        # Validate question structure
        required_fields = ["id", "type", "question", "answer", "explanation"]
        validated_questions = []
        
        for i, q in enumerate(questions):
            # Ensure each question has an id
            if "id" not in q:
                q["id"] = i + 1
            
            # Check required fields
            missing = [f for f in required_fields if f not in q]
            if missing:
                print(f"Question {i} missing fields: {missing}")
                continue  # Skip invalid questions
            
            # Add default options for MCQ if missing
            if q["type"] == "mcq" and (not q.get("options") or len(q["options"]) != 4):
                q["options"] = ["A) Option A", "B) Option B", "C) Option C", "D) Option D"]
            
            # Ensure options for true/false
            if q["type"] == "truefalse" and not q.get("options"):
                q["options"] = ["True", "False"]
            
            validated_questions.append(q)
        
        if not validated_questions:
            return jsonify({"error": "No valid questions could be extracted from the response"}), 500

        session["last_quiz"] = validated_questions
        return jsonify({
            "questions": validated_questions,
            "model_used": model,
            "model_info": ALL_MODELS.get(model, {}),
            "total_questions": len(validated_questions),
            "key_source": "environment" if api_key == ENV_GEMINI_API_KEY else "form"  # Let frontend know key source
        })

    except Exception as e:
        print(f"Unexpected error in generate_quiz: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/api/upload-pdf", methods=["POST"])
def upload_pdf():
    """Upload and extract text from PDF - Vercel compatible version"""
    try:
        # Check if on Vercel - PDF upload has limitations
        if IS_VERCEL:
            return jsonify({
                "warning": "PDF upload on Vercel has limitations. For large PDFs, please use text input instead.",
                "note": "Continuing with upload - file will be processed in /tmp"
            }), 200
        
        if "pdf" not in request.files:
            return jsonify({"error": "No file uploaded."}), 400

        file = request.files["pdf"]
        if file.filename == "":
            return jsonify({"error": "No file selected."}), 400
            
        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files are supported."}), 400

        # Check file size (limit to 5MB on Vercel, 10MB locally)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        max_size = 5 * 1024 * 1024 if IS_VERCEL else 10 * 1024 * 1024
        
        if file_size > max_size:
            return jsonify({
                "error": f"PDF file too large. Maximum size is {max_size // (1024*1024)}MB."
            }), 400

        # Save and process PDF
        filename = f"{uuid.uuid4()}.pdf"
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        try:
            text = extract_pdf_text(path)
            
            if not text or len(text.strip()) < 50:
                return jsonify({"error": "Could not extract enough text from PDF. The PDF might be image-based or empty."}), 400

            # Return preview (first 2000 chars) and full text
            preview = text[:2000] + ("..." if len(text) > 2000 else "")
            
            return jsonify({
                "text": text,
                "preview": preview,
                "word_count": len(text.split()),
                "character_count": len(text),
                "note": "Processed successfully" + (" on Vercel (temp storage)" if IS_VERCEL else "")
            })
            
        finally:
            # Clean up file
            if os.path.exists(path):
                os.remove(path)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"PDF upload error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500


@app.route("/api/evaluate", methods=["POST"])
def evaluate():
    """Evaluate user answers"""
    try:
        data = request.get_json()
        questions = data.get("questions", [])
        answers = data.get("answers", {})

        if not questions:
            return jsonify({"error": "No questions to evaluate"}), 400

        results = []
        score = 0

        for q in questions:
            qid = str(q["id"])
            user_ans = answers.get(qid, "").strip()
            correct = q["answer"].strip()
            
            # Normalize for comparison
            is_correct = user_ans.lower() == correct.lower()

            if is_correct:
                score += 1

            results.append({
                "id": q["id"],
                "question": q["question"],
                "type": q["type"],
                "user_answer": user_ans or "Not answered",
                "correct_answer": correct,
                "is_correct": is_correct,
                "explanation": q.get("explanation", "No explanation provided"),
                "options": q.get("options", [])
            })

        total = len(questions)
        percentage = round((score / total) * 100) if total > 0 else 0

        return jsonify({
            "score": score,
            "total": total,
            "percentage": percentage,
            "passed": percentage >= 70,
            "results": results,
            "feedback": get_feedback_message(percentage)
        })

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": f"Error evaluating answers: {str(e)}"}), 500


def get_feedback_message(percentage):
    """Generate feedback message based on score percentage"""
    if percentage >= 90:
        return "Excellent! You've mastered this topic!"
    elif percentage >= 80:
        return "Great job! You have a strong understanding."
    elif percentage >= 70:
        return "Good work! You've passed, but there's room for improvement."
    elif percentage >= 60:
        return "Fair attempt. Review the material and try again."
    else:
        return "Keep studying! Review the explanations and try the quiz again."


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": "2.0.0",
        "environment": "vercel" if IS_VERCEL else "local" if not IS_RENDER else "render",
        "models_available": len(ALL_MODELS),
        "gemini_models": len(FREE_GEMINI_MODELS),
        "gemma_models": len(GEMMA_MODELS),
        "env_key_configured": bool(ENV_GEMINI_API_KEY),
        "upload_folder": UPLOAD_FOLDER
    })


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# ──────────────────────────────────────────────
# Vercel serverless handler
# ──────────────────────────────────────────────
# This is what Vercel looks for
def handler(request, **kwargs):
    """Vercel serverless function handler"""
    return app(request.environ, request.start_response)


# ──────────────────────────────────────────────
# Render.com configuration (if still used)
# ──────────────────────────────────────────────
if IS_RENDER:
    # Running on Render - configure for production
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.logger.info("QuizGenius app started on Render")


# ──────────────────────────────────────────────
# Local development only
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Quiz Generator API - Powered by Google AI")
    print("=" * 60)
    print(f"\n📋 Available Models ({len(ALL_MODELS)} total):")
    print(f"   • Gemini Models: {len(FREE_GEMINI_MODELS)}")
    print(f"   • Gemma Models: {len(GEMMA_MODELS)}")
    print(f"\n🌍 Environment: {'Vercel' if IS_VERCEL else 'Render' if IS_RENDER else 'Local'}")
    
    # Show API key status
    if ENV_GEMINI_API_KEY:
        print(f"\n🔑 API Key: ✓ Found in .env file")
    else:
        print(f"\n🔑 API Key: ✗ Not found in .env file (will need to enter in form)")
    
    print("\n🚀 Featured Models:")
    
    # Show top models
    featured = ["models/gemini-2.5-flash", "models/gemini-2.5-pro", 
                "models/gemma-3-27b-it"]
    for model_id in featured:
        if model_id in ALL_MODELS:
            print(f"   ✓ {ALL_MODELS[model_id]['name']}")
    
    print("\n" + "=" * 60)
    
    # Local development
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Server starting at http://localhost:{port}")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print("=" * 60)
    
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)