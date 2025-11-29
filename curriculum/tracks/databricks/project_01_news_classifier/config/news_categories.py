"""
News classification categories and prompts for zero-shot learning
"""

# News categories for classification
NEWS_CATEGORIES = [
    "Politics",
    "Technology",
    "Business",
    "Sports",
    "Entertainment",
    "Health",
    "Science",
    "World News"
]

# Sentiment categories
SENTIMENT_CATEGORIES = [
    "Positive",
    "Neutral",
    "Negative"
]

# Zero-shot classification prompt template
CLASSIFICATION_PROMPT_TEMPLATE = """You are a news classification expert. Your task is to classify the following news article into ONE of these categories:

Categories: {categories}

News Article:
Title: {title}
Content: {content}

Instructions:
1. Read the article carefully
2. Choose the MOST appropriate category from the list above
3. Respond with ONLY the category name, nothing else

Category:"""

# Sentiment analysis prompt template
SENTIMENT_PROMPT_TEMPLATE = """You are a sentiment analysis expert. Your task is to determine the sentiment of the following news article.

Sentiment Options: {sentiments}

News Article:
Title: {title}
Content: {content}

Instructions:
1. Analyze the overall tone and sentiment of the article
2. Choose ONE sentiment from the options above
3. Respond with ONLY the sentiment name, nothing else

Sentiment:"""

# Combined classification prompt (category + sentiment)
COMBINED_PROMPT_TEMPLATE = """You are a news analysis expert. Analyze the following news article and provide both category and sentiment.

Categories: {categories}
Sentiments: {sentiments}

News Article:
Title: {title}
Content: {content}

Instructions:
1. Classify the article into the most appropriate category
2. Determine the overall sentiment
3. Respond in this exact format:
   Category: <category_name>
   Sentiment: <sentiment_name>

Response:"""