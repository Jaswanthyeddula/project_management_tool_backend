EXTRACT_TASK_FUNCTION = {
    "name": "extract_task",
    "description": "Extract structured task fields from natural language task input.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "A concise task title."
            },
            "description": {
                "type": "string",
                "description": "Additional detail about the task, if any. Empty string if none."
            },
            "due_date": {
                "type": "string",
                "description": "Due date in YYYY-MM-DD format. Empty string if not mentioned."
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "description": "One of low, medium, high, urgent. Default to 'medium' if not mentioned."
            },
            "assignee_name": {
                "type": "string",
                "description": "The name of the person to assign the task to. Empty string if not mentioned."
            }
        },
        "required": ["title"]
    }
}