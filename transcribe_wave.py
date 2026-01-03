import os
import sys
import wave
from pathlib import Path
from datetime import datetime
from gradio_client import Client
from gradio_client.utils import handle_file

# Configuration
# !!! REPLACE WITH YOUR HUGGING FACE SPACE URL !!!
HF_SPACE_URL = "https://dmajor007-audiotranscription.hf.space"
# Example: "https://username-whisper-api.hf.space"

# Audio processing parameters
CHUNK_SECONDS = 30  # Process in 30-second chunks
SAMPLE_RATE = 16000

def get_wav_info(wav_path):
    """Get WAV file information"""
    with wave.open(wav_path, 'rb') as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        nframes = wf.getnframes()
        duration = nframes / framerate
        
        return {
            'channels': channels,
            'sampwidth': sampwidth,
            'framerate': framerate,
            'nframes': nframes,
            'duration': duration
        }

def split_wav_into_chunks(wav_path, chunk_duration=30):
    """Split WAV file into chunks and return list of chunk files"""
    info = get_wav_info(wav_path)
    
    print(f"📊 WAV Info:")
    print(f"   Duration: {info['duration']:.2f} seconds")
    print(f"   Sample Rate: {info['framerate']} Hz")
    print(f"   Channels: {info['channels']}")
    print(f"   Sample Width: {info['sampwidth']} bytes")
    
    chunk_files = []
    
    with wave.open(wav_path, 'rb') as wf:
        frames_per_chunk = int(chunk_duration * info['framerate'])
        chunk_num = 0
        
        while True:
            frames = wf.readframes(frames_per_chunk)
            if not frames:
                break
            
            # Create temporary chunk file
            chunk_file = f"temp_chunk_{chunk_num}.wav"
            with wave.open(chunk_file, 'wb') as chunk_wf:
                chunk_wf.setnchannels(info['channels'])
                chunk_wf.setsampwidth(info['sampwidth'])
                chunk_wf.setframerate(info['framerate'])
                chunk_wf.writeframes(frames)
            
            chunk_files.append(chunk_file)
            chunk_num += 1
    
    return chunk_files, info['duration']

def transcribe_chunk(client, chunk_file):
    """Transcribe a single audio chunk using HF Space"""
    try:
        text = client.predict(
            handle_file(chunk_file)
        )
        return text if text else "[Silence or unclear audio]"
    except Exception as e:
        return f"[Transcription error: {e}]"

def transcribe_wav_file(wav_path, output_path=None, chunk_duration=30):
    """Transcribe entire WAV file"""
    
    # Verify input file exists
    if not os.path.exists(wav_path):
        print(f"❌ Error: File not found: {wav_path}")
        return 1
    
    # Set output path
    if output_path is None:
        base_name = Path(wav_path).stem
        output_path = f"{base_name}_transcript.txt"
    
    print("🎵 WAV File Transcription (Remote Whisper API)")
    print("=" * 60)
    print(f"📁 Input File: {wav_path}")
    print(f"📄 Output File: {output_path}")
    print(f"🤗 HF Space: {HF_SPACE_URL}")
    print("-" * 60)
    
    # Connect to HF Space
    print(f"🤗 Connecting to Hugging Face Space...")
    try:
        client = Client(HF_SPACE_URL)
        print("✅ Connected successfully\n")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return 1
    
    # Split WAV into chunks
    print("✂️  Splitting audio into chunks...")
    try:
        chunk_files, total_duration = split_wav_into_chunks(wav_path, chunk_duration)
        print(f"✅ Created {len(chunk_files)} chunks\n")
    except Exception as e:
        print(f"❌ Error splitting audio: {e}")
        return 1
    
    # Transcribe each chunk
    print("🎤 Starting transcription...")
    print("-" * 60)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"WAV File Transcription\n")
            f.write(f"Source: {wav_path}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {total_duration:.2f} seconds\n")
            f.write("=" * 60 + "\n\n")
            f.flush()
            
            # Process each chunk
            for i, chunk_file in enumerate(chunk_files):
                timestamp = i * chunk_duration
                
                print(f"[{timestamp:>5.1f}s] Processing chunk {i+1}/{len(chunk_files)}...")
                
                text = transcribe_chunk(client, chunk_file)
                
                output_line = f"[{timestamp:>5.1f}s] {text}"
                print(f"         {text}")
                
                f.write(output_line + "\n")
                f.flush()
        
        print("\n" + "=" * 60)
        print(f"✅ Transcription complete!")
        print(f"📄 Transcript saved to: {output_path}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Transcription stopped by user")
        print(f"💾 Partial transcript saved to: {output_path}")
    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        return 1
    finally:
        # Clean up temporary chunk files
        print("\n🧹 Cleaning up temporary files...")
        for chunk_file in chunk_files:
            try:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)
            except:
                pass
        print("✅ Cleanup complete")
    
    return 0

def main():
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python transcribe_wav.py <input.wav> [output.txt]")
        print("\nExample:")
        print("  python transcribe_wav.py recording.wav")
        print("  python transcribe_wav.py recording.wav transcript.txt")
        return 1
    
    wav_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Verify HF Space URL is set
    if "YOUR-USERNAME" in HF_SPACE_URL:
        print("❌ ERROR: Please set HF_SPACE_URL to your actual Hugging Face Space URL")
        print("   Edit the script and replace HF_SPACE_URL at the top")
        print("   Example: https://username-whisper-api.hf.space")
        return 1
    
    return transcribe_wav_file(wav_path, output_path)

if __name__ == "__main__":
    sys.exit(main())
