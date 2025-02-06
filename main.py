from flask import Flask, jsonify, request
import requests
from datetime import datetime, timedelta
import os
from openai import OpenAI
import threading
import json
from elevenlabs import ElevenLabs
import time

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def create_audio_from_text(text):
    """Background task to create audio using ElevenLabs API"""
    # Get timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract thinker's name from the first line of the text
    first_line = text.split('\n')[0]
    try:
        thinker_name = first_line.split("from")[1].strip().rstrip('.')
        # Clean the name for use in filename
        safe_filename = "".join(c for c in thinker_name if c.isalnum() or c.isspace()).strip()
        safe_filename = safe_filename.replace(" ", "_").lower()
        # Combine thinker name with timestamp
        safe_filename = f"{safe_filename}_{timestamp}"
    except:
        # Fallback to timestamp if we can't extract the name
        safe_filename = timestamp
    
    try:
        # Use our custom conversion that uses requests.post so we can control the timeout
        voice_id = "nPczCjzI2devNBz1zQrb"
        audio_bytes = convert_text_to_speech(voice_id, text)
        
        output_path = f"static/audio/{safe_filename}.mp3"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the audio file
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
            
        # Save success metadata
        metadata = {
            "thinker": thinker_name if 'thinker_name' in locals() else "unknown",
            "timestamp": timestamp,
            "file_path": output_path,
            "status": "completed"
        }
        
        with open(f"static/audio/{safe_filename}.json", "w") as f:
            json.dump(metadata, f)
            
    except Exception as e:
        print(f"Error in audio generation: {str(e)}")
        # Save detailed error metadata
        metadata = {
            "thinker": thinker_name if 'thinker_name' in locals() else "unknown",
            "timestamp": timestamp,
            "error": str(e),
            "status": "failed",
            "error_type": type(e).__name__
        }
        with open(f"static/audio/{safe_filename}.json", "w") as f:
            json.dump(metadata, f)

@app.route('/')
def index():
    return 'Two Thoughts Flask App!'

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
            latest_tweet = tweets_data['data'][0]
            
            # Generate monologue using OpenAI
            chat_completion = client.chat.completions.create(
                model="o1-mini",
                messages=[
                    {"role": "user", "content": """You are to generate a natural, 3-5 minute monologue for a podcast called "Two Thoughts." The monologue should focus on two quotes from a single thinker. Follow these instructions:
                        Introduction:
                          - Start with a single-line welcome: "Hi, welcome to another episode of 'Two Thoughts.' Today we have two thoughts from [THINKER'S NAME]."
                        Thinker's Background:
                          - Introduce the thinker, discussing their background, historical context, and significance.
                          - Cover their major achievements, influence, and key aspects that make this person relevant.
                        Two Quotes:
                          - Transition to the two quotes given in the input.
                          - Before analyzing each quote, read the exact quote out loud so listeners can follow along.
                        
                        Use the following as loose guidelines:
                        - Analyze each quote (meaning, relevance, interesting angles)
                        - Explore related or tangential topics that might be engaging for general listeners
                        - Look for connections or contradictions between the quotes (if any)
                        - Share any counterintuitive insights
                        - Generate any new ideas the quotes inspire
                        - Feel free to include any other interesting or related topics beyond these guidelines to keep listeners engaged.
                        
                        Format: This output will be sent to a text-to-speech model to generate audio, so format the output as something that will be heard, not read.
                        - Present as a continuous monologue, with natural pauses and transitions.
                        - Do not use any non-standard characters, such as slashes or escape sequences, and format the text into natural, readable English.

                        Use following techniques to improve output from a text-to-speech model:
                        - Use dashes (- or —) for short pauses or ellipses (…) when mentioning the two quotes. These help with keeping the quotes in focus.
                        - Ensure correct stress marking for multi-syllable words to maintain accurate pronunciation. As an example, a word like "trapezii" could be spelt "trapezIi" to put more emphasis on the "ii" of the word.
                        - Pacing can be controlled by writing in a natural, narrative style, similar to scriptwriting, to guide tone and pacing effectively.

                        Tone: Keep the tone casual, friendly, and humorous, as though it's an actual podcast.
                        - Aim for about 3-5 minutes of speaking time.
                        - The name of the podcast is "Two Thoughts"
                        - Keep it engaging and accessible.
                        
                        Here are the two quotes: """ + latest_tweet['text']}
                ]
            )
            
            conversation_text = chat_completion.choices[0].message.content
            
            # Start background task for audio generation
            thread = threading.Thread(
                target=create_audio_from_text,
                args=(conversation_text,)
            )
            thread.start()
            
            # Return response immediately without waiting for audio generation
            return jsonify({
                'tweet': latest_tweet,
                'conversation': conversation_text,
                'message': 'Audio generation started in background'
            })
        
        return jsonify({'error': 'No tweets found'}), 404
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

# Add a new endpoint to check audio generation status
@app.route('/audio-status/<filename>')
def audio_status(filename):
    json_path = f"static/audio/{filename}.json"
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            metadata = json.load(f)
        return jsonify(metadata)
    return jsonify({'status': 'not_found'}), 404

def convert_text_to_speech(voice_id, text):
    # Prepare API endpoint and headers based on the ElevenLabs API documentation
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": os.environ.get("ELEVENLABS_API_KEY"),
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128"
    }
    # Specify a tuple for (connect_timeout, read_timeout)
    response = requests.post(url, json=payload, headers=headers, timeout=(10, 180))
    response.raise_for_status()
    return response.content

if __name__ == '__main__':
    # Ensure the static/audio directory exists
    os.makedirs('static/audio', exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
