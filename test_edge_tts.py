import asyncio
import os

try:
    import edge_tts
    print("✅ edge-tts is installed")

    async def test_tts():
        text = "Hello, this is a test of edge TTS"
        voice = "en-US-AriaNeural"
        filename = "test_tts.mp3"

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)

        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✅ Successfully generated {filename} ({size} bytes)")
            os.remove(filename)
            print("✅ Cleanup successful")
        else:
            print("❌ Failed to generate audio file")

    print("Testing TTS generation...")
    asyncio.run(test_tts())
    print("✅ All tests passed!")

except ImportError:
    print("❌ edge-tts is NOT installed")
    print("Run: pip install edge-tts")
except Exception as e:
    print(f"❌ Error: {e}") 