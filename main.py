from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta
import os
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route('/')
def index():
    return 'Hello from Flask!'

@app.route('/tweets')
def get_tweets():
    # X API endpoint
    url = "https://api.x.com/2/tweets/search/recent"
    
    # Get time 24 hours ago in ISO format
    start_time = datetime.utcnow() - timedelta(days=1)
    
    # Query parameters
    params = {
        'query': 'from:jposhaughnessy "two thoughts from"',
        'start_time': start_time.isoformat() + 'Z',
        'tweet.fields': 'created_at,text'
    }
    
    # Headers with Bearer token
    headers = {
        'Authorization': f'Bearer {os.environ.get("X_BEARER_TOKEN")}'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        # Print for debugging
        print(f"URL: {response.url}")
        print(f"Status: {response.status_code}")
        response.raise_for_status()
        
        tweets_data = response.json()
        
        # Check if we got a tweet
        if 'data' in tweets_data and tweets_data['data']:
            latest_tweet = tweets_data['data'][0]  # This will be the most recent tweet
            
            # Generate conversation using OpenAI
            chat_completion = client.chat.completions.create(
                model="o1-mini",
                messages=[
                    {"role": "user", "content": """You are to generate a natural, 5-minute conversation between two people—Mark (male) and Sarah (female)—for a podcast called "Two Thoughts." The conversation should focus on two quotes from a single thinker. Follow these instructions:
                        Introduction:
                          - Start with a single-line welcome from Sarah: "Hi, welcome to another episode of 'Two Thoughts.' Today we have two thoughts from [THINKER’S NAME]."
                        Thinker’s Background:
                          - Have Sarah introduce the thinker to Mark immediately after the welcome, discussing their background, historical context, and significance.
                          - Discussion of Achievements and Influence
                          - Mark and Sarah exchange a few comments (2–3 messages) on the thinker’s major achievements, influence, or any key aspects that make this person relevant.
                        Two Quotes:
                          - Transition to the two quotes given in the input.
                          - Before analyzing each quote, read the exact quote out loud in the conversation so listeners can follow along.
                        
                        Use the following as loose guidelines:
                        - Analyze each quote (meaning, relevance, interesting angles)
                        - Explore related or tangential topics that might be engaging for general listeners
                        - Look for connections or contradictions between the quotes (if any)
                        - Share anecdotes or experiences, if helpful
                        - Share any counterintuitive insights
                        - Generate any new ideas the quotes inspire
                        - Feel free to include any other interesting or related topics beyond these guidelines to keep listeners engaged.
                        
                        Format: Present the conversation in dialogue form, with speaker names followed by their lines, like:
                        Sarah: [message]
                        Mark: [message]
                        
                        Tone: Keep the tone casual, friendly, and humorous, as though it’s an actual podcast.
                        - Aim for about 5 minutes of listening time.
                        - The name of the podcast is "Two Thoughts"
                        - Keep it engaging and accessible.
                        
                        Here are the two quotes: """ + latest_tweet['text']}
                ]
            )
            
            # Return just the latest tweet and conversation
            return jsonify({
                'tweet': latest_tweet,
                'conversation': chat_completion.choices[0].message.content
            })
        
        return jsonify({'error': 'No tweets found'}), 404
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
