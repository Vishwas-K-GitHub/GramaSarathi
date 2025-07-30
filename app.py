from flask import Flask, render_template, request, abort, redirect, url_for, session
import json
import os
# Import functions and variables from the local utils.py and translation_dict.py
from utils import filter_schemes, evaluate_step2
from translation_dict import translations

app = Flask(__name__)
app.secret_key = os.urandom(24) # Secret key for session management

# Define the base path for static and template files
# This helps in deployment and consistent file access
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Ensure Flask knows where to find templates and static files
app.template_folder = TEMPLATES_DIR
app.static_folder = STATIC_DIR

@app.route("/", methods=["GET"])
def index():
    """
    Renders the language selection page (index.html).
    """
    print("Loading index.html")
    return render_template("index.html")

@app.route("/form", methods=["GET"])
def form():
    """
    Renders the eligibility form page (form.html) based on the selected language.
    """
    try:
        lang = request.args.get("lang", "en")
        # Validate language, default to 'en' if invalid
        if lang not in translations:
            lang = "en"
        print(f"Loading form.html for language: {lang}")
        
        # Pass the entire translations dictionary for the selected language
        # This allows the template to access all translated strings
        return render_template("form.html", language=lang, translations=translations.get(lang))
    except Exception as e:
        print(f"Unexpected error in form route: {e}")
        # Render a generic error page or redirect with a message
        return render_template("error.html", message="An unexpected error occurred while loading the form.", language="en", translations=translations.get("en")), 500

@app.route("/results", methods=["POST"])
def results():
    """
    Processes user input from the form, filters schemes, and displays initial results.
    Stores matched schemes in session for step2 evaluation.
    """
    try:
        lang = request.form.get("language", "en")
        if lang not in translations:
            lang = "en"
        
        # Collect all user input from the form
        user_input = {
            "age": request.form.get("age"),
            "gender": request.form.get("gender"),
            "caste": request.form.get("caste"),
            "district": request.form.get("district"),
            "income": request.form.get("income"),
            "occupation": request.form.get("occupation"),
            "hk_quota": request.form.get("hk_quota"), # Not used in schemes.json eligibility, but collected
            "location": request.form.get("location")
        }

        # Load schemes data from schemes.json
        schemes_file_path = os.path.join(BASE_DIR, 'schemes.json')
        if not os.path.exists(schemes_file_path):
            print(f"Error: schemes.json not found at {schemes_file_path}")
            return render_template("error.html", message="Schemes data file not found.", language=lang, translations=translations.get(lang)), 404

        with open(schemes_file_path, "r", encoding="utf-8") as f:
            all_schemes = json.load(f)
        print(f"Loaded {len(all_schemes)} schemes from schemes.json")

        # Filter schemes using the improved logic from utils.py
        # The filter_schemes function now returns a dict with 'error' key if validation fails
        matched_schemes = filter_schemes(all_schemes, user_input)
        
        if isinstance(matched_schemes, dict) and "error" in matched_schemes:
            print(f"Validation error: {matched_schemes['error']}")
            # Redirect back to the form with an error message
            return render_template("form.html", language=lang, translations=translations.get(lang), error_message=matched_schemes['error'])

        print(f"Found {len(matched_schemes)} initially eligible schemes.")

        # Store the matched schemes in the session for subsequent step2 evaluation
        # This avoids re-filtering and ensures consistency
        session['matched_schemes'] = matched_schemes
        session['user_language'] = lang # Store language for consistent display

        # Pass the translations for the selected language to the template
        return render_template("results.html", language=lang, schemes=matched_schemes, translations=translations.get(lang), show_final=False)

    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"Data processing error in results: {e}")
        return render_template("error.html", message=f"Invalid input or data format error: {str(e)}", language=lang, translations=translations.get(lang)), 400
    except Exception as e:
        print(f"Unexpected error in results route: {e}")
        return render_template("error.html", message="An unexpected server error occurred.", language=lang, translations=translations.get(lang)), 500

@app.route("/finalize", methods=["POST"])
def finalize():
    """
    Evaluates second-step eligibility questions based on user answers and displays final eligible schemes.
    """
    try:
        lang = session.get('user_language', 'en') # Retrieve language from session
        if lang not in translations:
            lang = "en"

        # Retrieve matched schemes from session
        matched_schemes = session.get('matched_schemes', [])
        if not matched_schemes:
            # If session data is lost, redirect to form or show an error
            return redirect(url_for('index')) 

        # Collect answers for step2 questions
        step2_answers = {}
        for key, value in request.form.items():
            # Assuming scheme IDs are used as names for radio buttons in results.html
            if key.isdigit(): 
                step2_answers[key] = value
        
        # Evaluate step2 questions using the utility function
        # The evaluate_step2 function modifies the schemes in place by adding 'final_eligible' key
        final_evaluated_schemes = evaluate_step2(matched_schemes, step2_answers)
        
        # Filter to display only those schemes marked as 'final_eligible'
        final_display_schemes = [s for s in final_evaluated_schemes if s.get("final_eligible")]

        print(f"Found {len(final_display_schemes)} finally eligible schemes after step 2 evaluation.")

        # Render the results page again, but this time showing only final eligible schemes
        return render_template("results.html", language=lang, schemes=final_display_schemes, translations=translations.get(lang), show_final=True)

    except Exception as e:
        print(f"Unexpected error in finalize route: {e}")
        return render_template("error.html", message="An unexpected server error occurred during finalization.", language=lang, translations=translations.get(lang)), 500

if __name__ == "__main__":
    # When running locally, ensure the current working directory is 'project/'
    # or adjust paths accordingly.
    app.run(debug=True)

