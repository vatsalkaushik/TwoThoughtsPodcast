from flask import Flask, jsonify, request
import requests
from datetime import datetime, timedelta
import os
from openai import OpenAI
import threading
import json
from elevenlabs import ElevenLabs

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def create_audio_from_text(text):
    """Background task to create audio using ElevenLabs API"""
    try:
        # Initialize ElevenLabs client
        eleven_labs = ElevenLabs(
            api_key=os.environ.get("ELEVENLABS_API_KEY")
        )
        
        # Generate timestamp for the file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"static/audio/podcast_{timestamp}.mp3"
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convert text to speech and get the audio bytes
        audio_generator = eleven_labs.text_to_speech.convert(
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2"
        )
        
        # Convert generator to bytes
        audio_bytes = b"".join(chunk for chunk in audio_generator)
        
        # Save the audio file
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
            
        # Save metadata for tracking
        metadata = {
            "timestamp": timestamp,
            "file_path": output_path,
            "status": "completed"
        }
        
        with open(f"static/audio/podcast_{timestamp}.json", "w") as f:
            json.dump(metadata, f)
            
    except Exception as e:
        print(f"Error in audio generation: {str(e)}")
        # Save error metadata
        metadata = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "error": str(e),
            "status": "failed"
        }
        with open(f"static/audio/error_{timestamp}.json", "w") as f:
            json.dump(metadata, f)

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
            latest_tweet = tweets_data['data'][0]
            
            # Generate monologue using OpenAI
            # chat_completion = client.chat.completions.create(
            #     model="o1-mini",
            #     messages=[
            #         {"role": "user", "content": """You are to generate a natural, 5-minute monologue by Sarah for a podcast called "Two Thoughts." The monologue should focus on two quotes from a single thinker. Follow these instructions:
            #             Introduction:
            #               - Start with a single-line welcome: "Hi, welcome to another episode of 'Two Thoughts.' Today we have two thoughts from [THINKER'S NAME]."
            #             Thinker's Background:
            #               - Introduce the thinker, discussing their background, historical context, and significance.
            #               - Cover their major achievements, influence, and key aspects that make this person relevant.
            #             Two Quotes:
            #               - Transition to the two quotes given in the input.
            #               - Before analyzing each quote, read the exact quote out loud so listeners can follow along.
                        
            #             Use the following as loose guidelines:
            #             - Analyze each quote (meaning, relevance, interesting angles)
            #             - Explore related or tangential topics that might be engaging for general listeners
            #             - Look for connections or contradictions between the quotes (if any)
            #             - Share anecdotes or experiences, if helpful
            #             - Share any counterintuitive insights
            #             - Generate any new ideas the quotes inspire
            #             - Feel free to include any other interesting or related topics beyond these guidelines to keep listeners engaged.
                        
            #             Format: Present as a continuous monologue, with natural pauses and transitions.
                        
            #             Tone: Keep the tone casual, friendly, and humorous, as though it's an actual podcast.
            #             - Aim for about 5 minutes of speaking time.
            #             - The name of the podcast is "Two Thoughts"
            #             - Keep it engaging and accessible.
                        
            #             Here are the two quotes: """ + latest_tweet['text']}
            #     ]
            # )
            
            # conversation_text = chat_completion.choices[0].message.content
            conversation_text = "Hi, welcome to another episode of Two Thoughts. Today we have two thoughts from Mirza Ghalib. Now, if you're scratching your head wondering who Mirza Ghalib is, don't worry—you’re not alone! Mirza Ghalib was a towering figure in Urdu and Persian poetry during the Mughal Empire in India, living between 1797 and 1869. Born in what is now Uttar Pradesh, Ghalib navigated a time of immense cultural and political change. Despite the complex backdrop of British colonialism and the decline of the Mughal Empire, he crafted verses that still resonate today. Ghalib's poetry delves deep into themes of love, loss, philosophy, and the human condition, making him a beloved and enduring icon in South Asian literature. His influence extends beyond poetry into the broader realms of music and film, as his ghazals continue to inspire artists around the world.Alright, let's dive into our first quote:Lest we forget: It is easy to be human, very hard to be humane.Take a moment to let that sink in. It is easy to be human, very hard to be humane. At first glance, Ghalib is making a poignant observation about the difference between merely existing as a person and truly embodying kindness and compassion. Being human comes with all the inherent flaws, emotions, and complexities, but being humane? That's a different ballgame altogether. It requires empathy, selflessness, and a conscious effort to transcend our baser instincts.In today's fast-paced world, where social media can sometimes amplify our worst behaviors, Ghalib's words are a gentle reminder to strive for kindness. Think about it—technology makes it so easy to connect, yet genuine human connection can sometimes feel more elusive than ever. This quote challenges us to look beyond the surface and engage with others on a deeper level. It’s a call to action to not just survive, but to thrive in our relationships with empathy and understanding.And now, our second thought:The miracle of your absence is that I found myself whilst searching for you.Ah, love and loss—a classic Ghalib theme. The miracle of your absence is that I found myself whilst searching for you. This line beautifully captures the paradox of seeking someone so intensely that their absence becomes a catalyst for self-discovery. It suggests that in the quest to find another person, we often uncover parts of ourselves that were previously hidden or unexplored.Isn't that something we can all relate to? Think about those times when a relationship ends, and at first, it feels like the world has tipped on its axis. But gradually, you realize that this loss has given you the space to grow, to understand your own desires and needs better. Ghalib is highlighting that absence isn't just an empty space left behind; it's an opportunity for personal transformation.Now, if we look at both quotes together, there's a beautiful symmetry. The first quote is about the challenge of being truly humane, while the second is about finding oneself through absence. Perhaps Ghalib is suggesting that to become more humane, we sometimes need to step back and reflect on our own selves, especially in our interactions and relationships with others. It’s like he’s saying, To be truly kind and understanding, sometimes you need the space to understand yourself better.Let me share a quick anecdote. I once had a friend who moved abroad, and initially, our friendship felt strained by the distance. But over time, that separation allowed both of us to grow individually. When we reconnected, our relationship was stronger and more meaningful. It was like Ghalib's words came to life—through absence, we discovered more about who we are and what we need from each other.And here's a counterintuitive insight: sometimes, seeking connection so desperately can lead us away from true self-awareness. By focusing outward, we might neglect the inward journey that truly enriches our humanity. Ghalib seems to advocate for a balance—a harmony between connecting with others and cultivating our inner selves.These quotes inspire a new idea: what if we approached our relationships with the intention of not just finding others, but also finding ourselves? Imagine if every interaction was a step towards greater self-awareness and empathy. It could transform not only our personal lives but also the broader fabric of society.So, as we wrap up today's episode, let's take Mirza Ghalib's words to heart. Let's strive to be more humane, recognizing that it's a challenging but incredibly rewarding endeavor. And let's appreciate that in our quests for connection, we might just discover the most important connection of all—the one with ourselves."
            
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
@app.route('/audio-status/<timestamp>')
def audio_status(timestamp):
    json_path = f"static/audio/podcast_{timestamp}.json"
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            metadata = json.load(f)
        return jsonify(metadata)
    return jsonify({'status': 'not_found'}), 404

if __name__ == '__main__':
    # Ensure the static/audio directory exists
    os.makedirs('static/audio', exist_ok=True)
    app.run(host='0.0.0.0', port=5000)
