import re

TECH_KEYWORDS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "ruby", "go", "rust", "php", "swift",
    "react", "angular", "vue", "svelte", "next.js", "nuxt", "django", "flask", "fastapi", "spring",
    "express", "node.js", "kubernetes", "docker", "aws", "gcp", "azure", "terraform", "ansible",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "kafka", "rabbitmq"
}

def extract_technologies(text: str) -> list[str]:
    if not text:
        return []
    
    found = set()
    # Simple regex to find words, handling boundaries and some special chars like . or + or #
    words = re.findall(r'\b[a-zA-Z\.\+\#]+\b', text.lower())
    for word in words:
        if word in TECH_KEYWORDS:
            found.add(word)
            
    return list(found)
