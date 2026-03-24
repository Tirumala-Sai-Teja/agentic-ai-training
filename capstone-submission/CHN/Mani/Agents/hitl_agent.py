def human_review(state):
    print("\n[HITL] Review required!")
    
    # 1. Safely get the doc_type attribute from the class instance
    doc_type = getattr(state, "doc_type", "Unknown")
    print(f"Document Type: {doc_type}")
    print("\nExtracted Data:")

    # 2. Safely get extracted_data. If it's None or missing, default to {}
    extracted_data = getattr(state, "extracted_data", {})
    if extracted_data is None:
        extracted_data = {}

    # 3. Now it is safe to loop
    if not extracted_data:
        print("No data was extracted by the AI.")
    else:
        for k, v in extracted_data.items():
            print(f"  {k}: {v}")

    while True:
        decision = input("\nApprove? (y/n/edit): ").strip().lower()

        if decision == "y":
            # Update attributes directly if it's a standard class
            state.needs_review = False
            state.final_output = extracted_data
            break

        elif decision == "edit":
            # Working on a copy of the dict
            current_edits = dict(extracted_data)
            while True:
                field = input("Enter field to edit (or 'done'): ").strip()
                if field == "done":
                    break
                if field in current_edits:
                    new_value = input(f"New value for {field}: ")
                    current_edits[field] = new_value
                else:
                    print(f"Invalid field! Available: {list(current_edits.keys())}")
            
            state.extracted_data = current_edits
            state.needs_review = False
            state.final_output = current_edits
            break

        elif decision == "n":
            print("Marking for rejection...")
            state.final_output = {"status": "rejected"}
            state.needs_review = False
            break
        else:
            print("Invalid input. Please enter y / n / edit")

    return state