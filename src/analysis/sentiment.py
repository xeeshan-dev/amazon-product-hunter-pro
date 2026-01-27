from textblob import TextBlob
from typing import List, Dict

class SentimentAnalyzer:
    def analyze_reviews(self, reviews: List[str]) -> Dict:
        sentiments = [TextBlob(review).sentiment.polarity for review in reviews]
        
        return {
            'average_sentiment': sum(sentiments) / len(sentiments) if sentiments else 0,
            'positive_reviews': sum(1 for s in sentiments if s > 0),
            'neutral_reviews': sum(1 for s in sentiments if s == 0),
            'negative_reviews': sum(1 for s in sentiments if s < 0),
        }
    
    def analyze_review_topics(self, reviews: List[str]) -> Dict:
        # Implement basic topic extraction
        blob = TextBlob(' '.join(reviews))
        return {
            'common_phrases': blob.noun_phrases,
            'keywords': self._extract_keywords(blob)
        }
    
    def _extract_keywords(self, blob: TextBlob) -> List[str]:
        return [word for word, pos in blob.tags 
                if pos.startswith('NN') 
                and len(word) > 3]