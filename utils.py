def validate_input(data):
    """
    Validates user input data from the form.
    Returns True if valid, or an error message string if invalid.
    """
    try:
        # Age validation
        age_str = data.get("age")
        if not age_str:
            return "Age is a required field."
        try:
            age = int(age_str)
            if not (0 <= age <= 150):
                return "Age must be between 0 and 150."
        except ValueError:
            return "Invalid age value. Please enter a number."

        # Income validation
        income_str = data.get("income")
        if not income_str:
            return "Annual Income is a required field."
        try:
            income = int(income_str)
            if income < 0:
                return "Annual Income cannot be negative."
        except ValueError:
            return "Invalid annual income value. Please select a valid range."
            
        # Check for other required fields
        required_fields = ["gender", "caste", "district", "occupation", "location"]
        for field in required_fields:
            if not data.get(field):
                # Format field name nicely for error message
                display_field_name = field.replace('_', ' ').title()
                return f"Missing required field: {display_field_name}."
        
        return True # All validations passed
    except Exception as e:
        # Catch any unexpected errors during validation
        return f"An unexpected error occurred during input validation: {e}"

def filter_schemes(schemes, user_input):
    """
    Filters schemes based on user input criteria.
    Returns a list of eligible schemes or a dictionary with an 'error' key.
    """
    validation_result = validate_input(user_input)
    if isinstance(validation_result, str):
        return {"error": validation_result} # Return error message from validation

    filtered = []
    
    # Convert user input to appropriate types and lowercase for case-insensitive comparison
    age = int(user_input.get("age"))
    caste = user_input.get("caste", "").lower()
    gender = user_input.get("gender", "").lower()
    income = int(user_input.get("income"))
    occupation = user_input.get("occupation", "").lower()
    location = user_input.get("location", "").lower()
    # HK Quota is collected but not used in the provided schemes.json eligibility criteria.

    for scheme in schemes:
        elig = scheme.get("eligibility", {})
        is_eligible = True # Assume eligible until a criterion fails

        # 1. Age range check
        age_range = elig.get("age_range")
        if age_range and not (age_range[0] <= age <= age_range[1]):
            is_eligible = False

        # 2. Gender check
        scheme_genders = [g.lower() for g in elig.get("gender", [])]
        if scheme_genders and "all" not in scheme_genders and gender not in scheme_genders:
            is_eligible = False

        # 3. Caste check
        scheme_castes = [c.lower() for c in elig.get("caste", [])]
        if scheme_castes and "all" not in scheme_castes and caste not in scheme_castes:
            is_eligible = False

        # 4. Income check
        scheme_income_limit = elig.get("income_limit")
        if scheme_income_limit is not None:
            # If scheme_income_limit is a single value, user's income must be less than or equal to it
            if isinstance(scheme_income_limit, (int, float)):
                if income > scheme_income_limit:
                    is_eligible = False
            # If scheme_income_limit is a list (range), user's income must be within that range
            elif isinstance(scheme_income_limit, list) and len(scheme_income_limit) == 2:
                if not (scheme_income_limit[0] <= income <= scheme_income_limit[1]):
                    is_eligible = False

        # 5. Occupation check
        scheme_occupations = [o.lower() for o in elig.get("occupation", [])]
        if scheme_occupations and "any" not in scheme_occupations and occupation not in scheme_occupations:
            is_eligible = False

        # 6. Location check
        scheme_locations = [l.lower() for l in elig.get("location", [])]
        # If scheme_locations is empty, it means location is not a strict criterion for this scheme
        if scheme_locations and "all" not in scheme_locations and location not in scheme_locations:
            is_eligible = False
            
        if is_eligible:
            filtered.append(scheme)

    return filtered

def evaluate_step2(schemes, answers):
    """
    Evaluates second-step eligibility questions for a list of schemes.
    Adds a 'final_eligible' boolean key to each scheme dictionary.
    """
    for scheme in schemes:
        step2 = scheme.get("step2_question")
        if step2 and step2.get("question"):
            # The name attribute for radio buttons in results.html is the scheme ID
            question_id = str(scheme["id"]) 
            user_ans = answers.get(question_id, "").lower() # Get user's answer for this scheme's question
            expected = step2.get("expected_answer", "").lower() # Get the expected answer
            
            # Set final_eligible based on whether user's answer matches expected
            scheme["final_eligible"] = (user_ans == expected)
        else:
            # If a scheme has no step2 question, it's considered finally eligible
            scheme["final_eligible"] = True
    return schemes

