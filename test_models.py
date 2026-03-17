import google.generativeai as genai

API_KEY = "AIzaSyBh8cro2tZbqfB9_kUpYlKWYM0KRgQafQI"  # Replace with your key

try:
    genai.configure(api_key=API_KEY)
    models = genai.list_models()
    
    print("Available models:")
    for model in models:
        print(f"- {model.name}")
        print(f"  Display: {model.display_name}")
        print(f"  Methods: {model.supported_generation_methods}")
        print()
        
except Exception as e:
    print(f"Error: {e}")