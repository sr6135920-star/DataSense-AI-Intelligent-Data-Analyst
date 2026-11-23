"""
test_gemini.py
==============
Secure diagnostic test script for DataSense AI.
Verifies the Gemini API integration and environment variable setup
WITHOUT exposing or printing the raw API key.
"""

import os
import sys
from dotenv import load_dotenv

def test_connection():
    print("=" * 60)
    print("  DataSense AI – Gemini API Connection Test")
    print("=" * 60)

    # 1. Load .env file
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # 2. Check if key is configured
    if not api_key:
        print("\n❌ ERROR: 'GEMINI_API_KEY' was not found in your .env file.")
        print("💡 Solution:")
        print("   1. Open the '.env' file in this project folder.")
        print("   2. Add: GEMINI_API_KEY=your_actual_key_here")
        print("   3. Save the file and run this script again.\n")
        return False

    # Mask key for privacy (e.g., AIzaSy...7890)
    if len(api_key) > 10:
        masked_key = f"{api_key[:6]}...{api_key[-4:]} (Length: {len(api_key)} chars)"
    else:
        masked_key = "*** (Key appears too short)"
    
    print(f"\n🔑 API Key Detected: {masked_key}")
    print("📡 Connecting to Google Gemini API via official 'google-genai' SDK...")

    # 3. Test API call
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        models_to_test = [
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.8-flash",
        ]

        last_error = None
        for model_name in models_to_test:
            try:
                print(f"   -> Trying model: {model_name}...")
                response = client.models.generate_content(
                    model=model_name,
                    contents="Reply strictly in 6 words: DataSense AI Gemini connection verified successfully.",
                )
                if response and response.text:
                    print("\n" + "=" * 60)
                    print(f"✅ SUCCESS! Connected to Gemini API successfully.")
                    print(f"📌 Active Model : {model_name}")
                    print(f"🤖 AI Response  : {response.text.strip()}")
                    print("=" * 60)
                    print("\n🎉 Your DataSense AI application is ready to generate insights and chat!")
                    print("Run the app with: streamlit run app.py\n")
                    return True
            except Exception as model_err:
                last_error = model_err
                print(f"      (Model {model_name} notice: {str(model_err)[:100]}...)")
                continue

        # If all loop models failed
        print(f"\n❌ API Call Failed: {last_error}")
        _diagnose_error(str(last_error))
        return False

    except ImportError:
        print("\n❌ ERROR: 'google-genai' package is not installed.")
        print("💡 Solution: Run 'pip install google-genai python-dotenv'\n")
        return False
    except Exception as general_err:
        print(f"\n❌ Unexpected error: {general_err}")
        _diagnose_error(str(general_err))
        return False


def _diagnose_error(error_msg: str):
    print("\n🔍 Troubleshooting Guide:")
    if "API_KEY_INVALID" in error_msg or "400" in error_msg:
        print("   • Cause: The API key in .env appears to be invalid or mistyped.")
        print("   • Fix  : Double-check your key at https://aistudio.google.com/app/apikey")
    elif "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
        print("   • Cause: API rate limit or quota exceeded.")
        print("   • Fix  : Wait 60 seconds, or generate a fresh key on Google AI Studio.")
    elif "503" in error_msg or "UNAVAILABLE" in error_msg:
        print("   • Cause: Temporary high demand on Google servers.")
        print("   • Fix  : The app will automatically try alternate models (3.5-flash-lite).")
    elif "getaddrinfo failed" in error_msg or "ConnectError" in error_msg:
        print("   • Cause: No internet connection.")
        print("   • Fix  : Check your network/Wi-Fi connection and firewall.")
    else:
        print(f"   • Details: {error_msg}")


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
