"""Execute allowlisted, reproducible peak-edit recipes."""
def apply_recipe(editor, recipe):
    if not isinstance(recipe, dict) or recipe.get("schema_version", 1) != 1:
        raise ValueError("Recipe must be a schema_version 1 object.")
    if set(recipe) - {"schema_version", "description", "initial_peaks", "operations"}:
        raise ValueError("Unknown recipe fields; use description, initial_peaks, and operations.")
    initial, operations = recipe.get("initial_peaks", []), recipe.get("operations", [])
    if not isinstance(initial, list) or not isinstance(operations, list):
        raise ValueError("initial_peaks and operations must be lists.")
    for specification in initial:
        if not isinstance(specification, dict):
            raise ValueError("Each initial peak must be an object.")
        editor.execute("insert_peak", **specification)
    before = editor.snapshot()
    for index, command in enumerate(operations, 1):
        if not isinstance(command, dict) or "op" not in command:
            raise ValueError(f"Operation {index} requires an op field.")
        parameters = {key: value for key, value in command.items() if key != "op"}
        try:
            editor.execute(command["op"], **parameters)
        except ValueError as error:
            raise ValueError(f"Operation {index} ({command['op']}): {error}") from error
    return before
