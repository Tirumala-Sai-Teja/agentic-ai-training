def validate(state):
    print("[Validator] Validating extracted data...")

    # 1. Safely get the data from the class instance
    data = getattr(state, "extracted_data", {})
    
    # 2. Check if the dictionary has any actual values (not just empty strings)
    # This filters out {"authorizer": "", "date": ""}
    has_content = data and any(value for value in data.values() if value)

    if has_content:
        # If we have at least some data, give it a passing grade
        state.confidence = 0.9
        state.needs_review = False
        print("Validation passed.")
    else:
        # If data is empty or all fields are blank, force Human Review
        state.confidence = 0.3
        state.needs_review = True
        print("Validation failed: No data extracted.")

    return state