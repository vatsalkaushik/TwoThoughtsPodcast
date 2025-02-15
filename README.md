# Two Thoughts Podcast Generator

An automated system that generates podcast episodes from Twitter/X posts using AI for content generation and text-to-speech conversion.

## Features

- Fetches recent "Two Thoughts" tweets from @jposhaughnessy's account daily
- Generates podcast transcript using OpenAI's API
- Converts text to speech using ElevenLabs
- Uploads episodes to Captivate FM

## Prerequisites

- Python 3.8+
- Flask
- OpenAI API access
- ElevenLabs API access
- Twitter/X API access
- Captivate FM API access

## Environment Variables

The following environment variables are required:

- `OPENAI_API_KEY`: OpenAI API key for generating conversation
- `APP_API_KEY`: API key for securing endpoints
- `X_BEARER_TOKEN`: Twitter/X API bearer token
- `ELEVENLABS_API_KEY`: ElevenLabs API key for text-to-speech
- `CAPTIVATE_USER_ID`: Captivate FM user ID
- `CAPTIVATE_API_TOKEN`: Captivate FM API token
- `CAPTIVATE_SHOW_ID`: Captivate FM show ID