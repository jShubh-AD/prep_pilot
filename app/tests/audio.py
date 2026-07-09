import asyncio
from google import genai
from google.genai import types
from app.core.settings import settings

config = types.LiveConnectConfig(
    response_modalities=[
        "AUDIO",
    ],
    output_audio_transcription={},
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=104857,
        sliding_window=types.SlidingWindow(target_tokens=52428),
    ),
)
client = genai.Client(api_key=settings.GEMINI_API_KEY)

async def main():
    async with client.aio.live.connect(
        model="models/gemini-3.1-flash-live-preview",
        config=config
    ) as session:
        
        while True:
            user_input = await asyncio.to_thread(input, "user message: ")

            if user_input == "q":
                break

            await session.send_client_content(
                turns=types.Content(
                role='user',
                parts=[types.Part(text=user_input)]),
                turn_complete=True,
            )

            async for event in session.receive():
                if event.server_content:
                    print("="*50, end="")
                    print("AUDIO", end="")
                    print("="*50)
                    if event.server_content.model_turn:
                        print(event.server_content.model_turn.parts[0].inline_data.data)
                if event.server_content and (event.server_content.turn_complete or event.server_content.interrupted):
                    pass

asyncio.run(main())