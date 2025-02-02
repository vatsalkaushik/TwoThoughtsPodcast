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
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant engaging in a conversation about a tweet. Provide thoughtful insights and ask relevant questions about the content."},
                    {"role": "user", "content": f"Let's discuss this tweet: {latest_tweet['text']}"}
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
