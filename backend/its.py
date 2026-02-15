def apply_its_mode(question: str, mode: str) -> str:
    if mode == "hint":
        return f"Give a helpful hint without revealing the full answer.\n\nQuestion:\n{question}"

    if mode == "socratic":
        return f"Guide the student using questions instead of direct answers.\n\nQuestion:\n{question}"

    return question
