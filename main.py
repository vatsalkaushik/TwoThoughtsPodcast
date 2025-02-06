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

def get_captivate_auth_token():
    """Get authentication token from Captivate"""
    url = "https://api.captivate.fm/authenticate/token"
    
    try:
        user_id = os.environ.get("CAPTIVATE_USER_ID")
        api_token = os.environ.get("CAPTIVATE_API_TOKEN")
        
        if not user_id or not api_token:
            raise ValueError("Captivate user ID or API token not found in environment variables")
        
        data = {
            'username': user_id,
            'token': api_token
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        auth_data = response.json()
        return auth_data['user']['token']
    except Exception as e:
        print(f"Error getting Captivate auth token: {str(e)}")
        return None

def create_captivate_episode(media_data, thinker_name):
    """Create a new episode in Captivate FM"""
    url = "https://api.captivate.fm/episodes"
    
    try:
        # Get fresh authentication token
        auth_token = get_captivate_auth_token()
        if not auth_token:
            raise ValueError("Failed to get Captivate authentication token")
        
        # Format current date with 8 AM time
        current_date = datetime.now().strftime("%Y-%m-%d")
        publish_datetime = f"{current_date} 08:00:00"
        
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        
        show_notes = (
            f"Two Thoughts from {thinker_name} — curated by Jim O'Shaughnessy, "
            "brought to life through AI narration and analysis.\n\n"
            "Buy Two Thoughts on Amazon (https://amzn.id/BMLcqU6) or on infinitebooks.com"
        )
        
        payload = {
            'shows_id': os.environ.get("CAPTIVATE_SHOW_ID"),
            'title': f'Two Thoughts from {thinker_name}',
            'media_id': media_data['media']['id'],
            'date': publish_datetime,
            'shownotes': show_notes,
            'summary': f'Exploring two thought-provoking quotes from {thinker_name}',
            'author': 'Two Thoughts AI',
            'episode_type': 'full',
            'explicit': 'false',
            'itunes_block': 'false'
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error creating Captivate episode: {str(e)}")
        return None

def upload_to_captivate(file_path, show_id):
    """Upload audio file to Captivate FM"""
    url = f"https://api.captivate.fm/shows/{show_id}/media"
    
    try:
        # Get fresh authentication token
        auth_token = get_captivate_auth_token()
        if not auth_token:
            raise ValueError("Failed to get Captivate authentication token")
            
        headers = {
            'Authorization': f'Bearer {auth_token}'
        }
        
        with open(file_path, 'rb') as audio_file:
            files = {'file': audio_file}
            response = requests.post(url, files=files, headers=headers)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error uploading to Captivate: {str(e)}")
        return None

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
            
        # Upload to Captivate FM
        show_id = os.environ.get("CAPTIVATE_SHOW_ID")
        if show_id:
            # First upload the media file
            media_response = upload_to_captivate(output_path, show_id)
            
            # If media upload successful, create the episode
            if media_response and media_response.get('success'):
                episode_response = create_captivate_episode(media_response, thinker_name)
                captivate_response = {
                    'media': media_response,
                    'episode': episode_response
                }
            else:
                captivate_response = {'media': media_response, 'error': 'Media upload failed'}
                
            metadata = {
                "thinker": thinker_name if 'thinker_name' in locals() else "unknown",
                "timestamp": timestamp,
                "file_path": output_path,
                "status": "completed",
                "captivate": captivate_response
            }
        else:
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

@app.route('/todays-tt')
def get_tweets():
    url = "https://api.x.com/2/tweets/search/recent"
    
    # Get time 24 hours ago in ISO format
    start_time = datetime.utcnow() - timedelta(days=1)
    
    params = {
        'query': '"two thoughts from" from:jposhaughnessy',
        'start_time': start_time.isoformat() + 'Z',
        'tweet.fields': 'created_at,text'
    }
    
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
                          - Start with a single-line welcome: "Hi... Welcome to another episode of 'Two Thoughts.' Today we have two thoughts from [THINKER'S NAME]."
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

@app.route('/test-captivate-upload')
def test_captivate_upload():
    """Test endpoint to upload an existing audio file to Captivate"""
    test_file = "static/audio/jim_harrison_20250206_124948.mp3"
    
    if not os.path.exists(test_file):
        return jsonify({'error': 'Test file not found'}), 404
        
    show_id = os.environ.get("CAPTIVATE_SHOW_ID")
    if not show_id:
        return jsonify({'error': 'CAPTIVATE_SHOW_ID not set'}), 500
        
    try:
        # First upload the media file
        media_response = upload_to_captivate(test_file, show_id)
        
        # If media upload successful, create the episode
        if media_response and media_response.get('success'):
            episode_response = create_captivate_episode(media_response, "Jim Harrison")
            return jsonify({
                'media': media_response,
                'episode': episode_response
            })
        else:
            return jsonify({
                'error': 'Media upload failed',
                'media_response': media_response
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-episode-creation')
def test_episode_creation():
    """Test endpoint to create an episode with specific media ID"""
    try:
        # Mock media response data structure
        media_data = {
            'media': {
                'id': '4a5f8091-a955-4459-9418-00aa913a2af2'
            },
            'success': True
        }
        
        # Create episode with test data
        episode_response = create_captivate_episode(media_data, "Jim Harrison")
        
        return jsonify({
            'status': 'success',
            'episode': episode_response
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

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
