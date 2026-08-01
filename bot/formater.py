def format_project(project):

    return f"""
📌 {project['title']}

💰 Budget: {project['max_budget']}

📝 Description:

{project['description']}

🔗 {project['shortened_url']}
"""